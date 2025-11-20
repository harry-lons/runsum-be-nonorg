from flask import Flask, request, jsonify, make_response, g
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, set_access_cookies, unset_jwt_cookies
from dotenv import load_dotenv
from stravalib import Client
from flask_cors import CORS
from datetime import datetime, timedelta
import helpers as h
from db import db_utils as db
import os
import logging
import argparse
import time

load_dotenv()
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
FRONTEND_URL = os.getenv('FRONTEND_URL')
SECURE = os.getenv('SECURE') == 'true' # convert t/f string to boolean
JWT_SECRET = os.getenv('JWT_SECRET')

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

app = Flask(__name__)

# Enable CORS - simplified for same-origin deployment
# When both frontend and backend are on runsum.harrylons.com, CORS is minimal
# Still allow FRONTEND_URL for backward compatibility during transition
CORS(app, resources={r"/*": {"origins": [FRONTEND_URL, "https://runsum.harrylons.com", "http://localhost:3010"]}}, 
     supports_credentials=True,
     expose_headers=['Set-Cookie'])

# Add after_request handler to ensure CORS headers are present on ALL responses (including redirects)
@app.after_request
def after_request(response):
    """Ensure CORS headers are present on all responses, including errors and redirects"""
    origin = request.headers.get('Origin')
    allowed_origins = [FRONTEND_URL, "https://runsum.harrylons.com", "http://localhost:3010"]
    if origin in allowed_origins:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-CSRF-TOKEN'
        response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    return response

# Flask-JWT-Extended configuration
app.config['JWT_SECRET_KEY'] = JWT_SECRET
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
app.config["JWT_COOKIE_SECURE"] = SECURE

# For same-origin deployment (frontend and backend on same domain), use Lax
# This is more secure and works better with mobile browsers
SAMESITE_SETTING = "Lax"

app.config["JWT_COOKIE_SAMESITE"] = SAMESITE_SETTING
app.config["JWT_COOKIE_CSRF_PROTECT"] = True  # Keep CSRF protection enabled

# Cookie Domain - set to .harrylons.com to work across subdomains in production
# For local dev, None (default) is fine
COOKIE_DOMAIN = ".harrylons.com" if SECURE else None
app.config["JWT_COOKIE_DOMAIN"] = COOKIE_DOMAIN

# CSRF Cookie Configuration - must match JWT cookie settings
app.config["JWT_CSRF_IN_COOKIES"] = True
app.config["JWT_CSRF_CHECK_FORM"] = False  # Only check headers
app.config["JWT_ACCESS_CSRF_COOKIE_NAME"] = "csrf_access_token"
app.config["JWT_ACCESS_CSRF_COOKIE_PATH"] = "/"
app.config["JWT_ACCESS_CSRF_COOKIE_SAMESITE"] = SAMESITE_SETTING  # Must match JWT cookie
app.config["JWT_ACCESS_CSRF_COOKIE_SECURE"] = SECURE  # Must match JWT cookie
app.config["JWT_ACCESS_CSRF_COOKIE_DOMAIN"] = COOKIE_DOMAIN  # Must match JWT cookie

jwt = JWTManager(app)

# JWT error handlers
@jwt.unauthorized_loader
def unauthorized_callback(callback):
    logger.warning(f"Unauthorized access attempt: {callback}")
    logger.debug(f"Request cookies: {request.cookies}")
    return jsonify({"error": "Missing or invalid authentication token"}), 401

@jwt.invalid_token_loader
def invalid_token_callback(callback):
    logger.warning(f"Invalid token: {callback}")
    return jsonify({"error": "Invalid authentication token"}), 401

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    logger.warning(f"Expired token for user: {jwt_payload.get('sub', 'unknown')}")
    return jsonify({"error": "Token has expired"}), 401

# Strava client
auth_client = Client()

@app.route("/")
def home():
    return "Hello HTTPS!"

@app.route("/api/health")
def health_check():
    """Lightweight health check endpoint for uptime monitoring"""
    return {"status": "ok", "service": "runsum-backend"}, 200

###############
# AUTH ROUTES #
###############

@app.route("/api/auth/login", methods=['POST'])
def authenticate_me():
    try:
        logger.info("Login attempt received")
        data = request.get_json()
        code = data['code']
        logger.debug(f"Auth code received (length: {len(code)})")
        
        # Exchange auth code for Strava tokens
        logger.info("Exchanging auth code for Strava tokens")
        acc_tok, ref_tok, exp_at = h.get_token_from_code(
            auth_client, code, CLIENT_ID=CLIENT_ID, CLIENT_SECRET=CLIENT_SECRET
        )
        logger.debug(f"Access token obtained (expires at: {exp_at})")
        
        temp_client = Client(access_token=acc_tok)
        logger.info("Fetching athlete information from Strava")
        athlete = temp_client.get_athlete()
        logger.info(f"Athlete fetched: {athlete.firstname} {athlete.lastname} (ID: {athlete.id})")
        
        # Create or update athlete in database
        existing_athlete = db.get_athlete_by_id(athlete.id)
        if existing_athlete:
            logger.info(f"Updating existing athlete in database (ID: {athlete.id})")
            db.update_athlete_tokens(athlete.id, acc_tok, ref_tok, exp_at)
            db.update_athlete_name(athlete.id, athlete.firstname, athlete.lastname)
        else:
            logger.info(f"Creating new athlete in database (ID: {athlete.id})")
            db.create_athlete(
                athlete.id, 
                athlete.firstname, 
                athlete.lastname,
                acc_tok, 
                ref_tok, 
                exp_at
            )
        
        # Create JWT for session management
        athleteIdentity = {
            "id": athlete.id,
            "first_name": athlete.firstname
        }
        logger.info("Creating JWT for session management")
        JWT = create_access_token(identity=athleteIdentity, expires_delta=timedelta(days=30))
        
        resp = jsonify({
            "first_name": athlete.firstname, 
            "id": athlete.id,
            "success": True
        })
        set_access_cookies(resp, JWT)
        logger.info(f"Login successful for athlete ID: {athlete.id}")
        
        return resp, 200
    
    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to authenticate"}), 500
    
@app.route('/api/auth/logout', methods=['POST'])
def logout_with_cookies():
    logger.info("Logout request received")
    response = jsonify({"msg": "logout successful"})
    unset_jwt_cookies(response)
    
    # Manually clear cookies with explicit domain settings for production
    # This ensures cookies are properly cleared with the same domain they were set with
    if COOKIE_DOMAIN:
        # Clear the JWT access token cookie
        response.set_cookie(
            'access_token_cookie',
            value='',
            max_age=0,
            expires=0,
            path='/',
            domain=COOKIE_DOMAIN,
            secure=SECURE,
            httponly=True,
            samesite=SAMESITE_SETTING
        )
        # Clear the CSRF token cookie
        response.set_cookie(
            'csrf_access_token',
            value='',
            max_age=0,
            expires=0,
            path='/',
            domain=COOKIE_DOMAIN,
            secure=SECURE,
            httponly=False,  # CSRF tokens are not httponly
            samesite=SAMESITE_SETTING
        )
    
    logger.info("Logout successful")
    return response
    
@app.route('/api/auth/whoami', methods=['GET'])
@jwt_required()
def who_am_i():
    try:
        logger.info("Who am I request received")
        user = get_jwt_identity()
        logger.debug(f"JWT identity: {user}")
        athlete = db.get_athlete_by_id(user["id"])
        
        if not athlete:
            logger.warning(f"User not found in database (ID: {user['id']})")
            return jsonify({"error": "User not found in database"}), 404
        
        logger.info(f"User information fetched for athlete ID: {athlete['strava_id']}")
        resp = make_response(
            jsonify({
                "first_name": athlete['firstname'],
                "last_name": athlete['lastname'],
                "id": athlete['strava_id'],
                "success": True
            })
        )
        return resp, 200
    
    except Exception as e:
        logger.error(f"Failed to fetch user information: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to fetch user information"}), 500

##############
# ACTIVITIES #
##############
@app.route('/api/activities', methods=['GET'])
@jwt_required()
def get_activities():
    request_start = time.time()
    try:
        logger.info(f"[TIMING] Get activities request received - Page {request.args.get('page')}")
        after = request.args.get('after')
        before = request.args.get('before')
        page = request.args.get('page')
        logger.debug(f"Query parameters - after: {after}, before: {before}")
        
        if before is None or after is None:
            logger.warning("Missing date parameters in request")
            return jsonify({"msg": "Missing start or end date in request"}), 400 # 400 Bad Request

        if page is None:
            logger.warning("Missing page parameter in request")
            return jsonify({"msg": "Missing page parameter in activities request"}), 400 # 400 Bad Request
        
        db_start = time.time()
        user = get_jwt_identity()
        logger.debug(f"User identity: {user}")
        athlete = db.get_athlete_by_id(user["id"])
        db_duration = (time.time() - db_start) * 1000
        logger.info(f"[TIMING] Database lookup: {db_duration:.2f}ms")
        
        if not athlete:
            logger.warning(f"User not found in database (ID: {user['id']})")
            return jsonify({"error": "User not found in database"}), 404
        
        now = datetime.now()
        expires_at = athlete['expires_at']
        
        if expires_at <= now:
            # Token is expired, refresh it
            logger.info("Access token expired, refreshing...")
            token_refresh_start = time.time()
            new_access_token, new_expires_at = h.refresh_strava_token(
                athlete['refresh_token'], CLIENT_ID, CLIENT_SECRET
            )
            # Update database with new access token (refresh token stays the same)
            db.update_athlete_tokens(user["id"], new_access_token, athlete['refresh_token'], new_expires_at)
            # Update athlete dict with new access token for this request
            athlete['access_token'] = new_access_token
            athlete['expires_at'] = new_expires_at
            token_refresh_duration = (time.time() - token_refresh_start) * 1000
            logger.info(f"[TIMING] Token refresh: {token_refresh_duration:.2f}ms")

        fetch_start = time.time()
        activities_list = h.fetch_activities(athlete, after, before, page=page)
        fetch_duration = (time.time() - fetch_start) * 1000
        logger.info(f"[TIMING] Total fetch_activities call: {fetch_duration:.2f}ms")
        
        h.log_query(athlete["strava_id"], after, before)
        
        json_start = time.time()
        response_data = jsonify({
            "activities": activities_list,
            "count": len(activities_list),
            "success": True
        })
        json_duration = (time.time() - json_start) * 1000
        logger.info(f"[TIMING] JSON serialization: {json_duration:.2f}ms")
        
        total_duration = (time.time() - request_start) * 1000
        logger.info(f"[TIMING] Total endpoint time (page {page}): {total_duration:.2f}ms - Returned {len(activities_list)} activities")
        
        return response_data, 200
    
    except Exception as e:
        logger.error(f"Failed to fetch activities: {str(e)}", exc_info=True)
        return jsonify({"error": f"Failed to fetch activities: {str(e)}"}), 500

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Run the Runsum backend server')
    parser.add_argument('-v', '--verbose', action='store_true', 
                        help='Enable verbose mode for detailed logging')
    args = parser.parse_args()
    
    # Set logging level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("Verbose mode enabled - logging level set to DEBUG")
    else:
        logging.getLogger().setLevel(logging.INFO)
    
    # Use PORT from environment (Render provides this), default to 3011 for local
    port = int(os.getenv('PORT', 3011))
    
    logger.info(f"Starting server on port {port}")
    logger.info(f"Frontend URL: {FRONTEND_URL}")
    logger.info(f"Secure mode: {SECURE}")
    
    # Use 0.0.0.0 to accept connections from any IP (required for cloud hosting)
    # Disable debug mode in production (check RENDER env var)
    debug_mode = not bool(os.getenv('RENDER'))
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
