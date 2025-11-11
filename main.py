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

# Enable CORS
CORS(app, resources={r"/*": {"origins": FRONTEND_URL}}, 
     supports_credentials=True,
     expose_headers=['Set-Cookie'])

# Add after_request handler to ensure CORS headers are present on ALL responses (including redirects)
@app.after_request
def after_request(response):
    """Ensure CORS headers are present on all responses, including errors and redirects"""
    origin = request.headers.get('Origin')
    if origin == FRONTEND_URL:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-CSRF-TOKEN'
        response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    return response

# Flask-JWT-Extended configuration
app.config['JWT_SECRET_KEY'] = JWT_SECRET
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
app.config["JWT_COOKIE_SECURE"] = SECURE

# SameSite=None requires Secure=True in modern browsers
# For local dev (HTTP), use Lax; for production (HTTPS), use None for cross-origin
SAMESITE_SETTING = "None" if SECURE else "Lax"

app.config["JWT_COOKIE_SAMESITE"] = SAMESITE_SETTING
app.config["JWT_COOKIE_CSRF_PROTECT"] = True  # Keep CSRF protection enabled

# CSRF Cookie Configuration - must match JWT cookie settings
app.config["JWT_CSRF_IN_COOKIES"] = True
app.config["JWT_CSRF_CHECK_FORM"] = False  # Only check headers
app.config["JWT_ACCESS_CSRF_COOKIE_NAME"] = "csrf_access_token"
app.config["JWT_ACCESS_CSRF_COOKIE_PATH"] = "/"
app.config["JWT_ACCESS_CSRF_COOKIE_SAMESITE"] = SAMESITE_SETTING  # Must match JWT cookie
app.config["JWT_ACCESS_CSRF_COOKIE_SECURE"] = SECURE  # Must match JWT cookie

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

@app.route("/health")
def health_check():
    """Lightweight health check endpoint for uptime monitoring"""
    return {"status": "ok", "service": "runsum-backend"}, 200

###############
# AUTH ROUTES #
###############

@app.route("/auth/login", methods=['POST'])
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
    
@app.route('/auth/logout', methods=['POST'])
def logout_with_cookies():
    logger.info("Logout request received")
    response = jsonify({"msg": "logout successful"})
    unset_jwt_cookies(response)
    logger.info("Logout successful")
    return response
    
@app.route('/auth/whoami', methods=['GET'])
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
@app.route('/activities', methods=['GET'])
@jwt_required()
def get_activities():
    try:
        logger.info("Get activities request received")
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
        
        user = get_jwt_identity()
        logger.debug(f"User identity: {user}")
        athlete = db.get_athlete_by_id(user["id"])
        
        if not athlete:
            logger.warning(f"User not found in database (ID: {user['id']})")
            return jsonify({"error": "User not found in database"}), 404
        
        now = datetime.now()
        expires_at = athlete['expires_at']
        
        if expires_at <= now:
            # Token is expired, refresh it
            logger.info("Access token expired, refreshing...")
            new_access_token, new_expires_at = h.refresh_strava_token(
                athlete['refresh_token'], CLIENT_ID, CLIENT_SECRET
            )
            # Update database with new access token (refresh token stays the same)
            db.update_athlete_tokens(user["id"], new_access_token, athlete['refresh_token'], new_expires_at)
            # Update athlete dict with new access token for this request
            athlete['access_token'] = new_access_token
            athlete['expires_at'] = new_expires_at
            logger.info("Access token refreshed successfully")

        activities_list = h.fetch_activities(athlete, after, before, page=page)
        
        logger.info(f"Successfully fetched {len(activities_list)} activities")
        return jsonify({
            "activities": activities_list,
            "count": len(activities_list),
            "success": True
        }), 200
    
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
