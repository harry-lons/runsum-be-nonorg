from flask import Flask, request, jsonify, make_response, g
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, set_access_cookies, unset_jwt_cookies
from dotenv import load_dotenv
from stravalib import Client
from flask_cors import CORS
from datetime import datetime, timedelta
import helpers as h
from db import db_utils as db
import os

load_dotenv()
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
FRONTEND_URL = os.getenv('FRONTEND_URL')
SECURE = os.getenv('SECURE') == 'true' # convert t/f string to boolean
JWT_SECRET = os.getenv('JWT_SECRET')

app = Flask(__name__)

# Enable CORS
CORS(app, resources={r"/*": {"origins": FRONTEND_URL}}, 
     supports_credentials=True,
     expose_headers=['Set-Cookie'])

# Flask-JWT-Extended configuration
app.config['JWT_SECRET_KEY'] = JWT_SECRET
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
app.config["JWT_COOKIE_SECURE"] = SECURE

jwt = JWTManager(app)

# Strava client
auth_client = Client()

@app.route("/")
def home():
    return "Hello HTTPS!"

###############
# AUTH ROUTES #
###############

@app.route("/auth/login", methods=['POST'])
def authenticate_me():
    try:
        data = request.get_json()
        code = data['code']
        
        # Exchange auth code for Strava tokens
        acc_tok, ref_tok, exp_at = h.get_token_from_code(
            auth_client, code, CLIENT_ID=CLIENT_ID, CLIENT_SECRET=CLIENT_SECRET
        )
        
        temp_client = Client(access_token=acc_tok)
        athlete = temp_client.get_athlete()
        
        # Create or update athlete in database
        existing_athlete = db.get_athlete_by_id(athlete.id)
        if existing_athlete:
            db.update_athlete_tokens(athlete.id, acc_tok, ref_tok, exp_at)
            db.update_athlete_name(athlete.id, athlete.firstname, athlete.lastname)
        else:
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
        JWT = create_access_token(identity=athleteIdentity, expires_delta=timedelta(days=30))
        
        resp = jsonify({
            "first_name": athlete.firstname, 
            "id": athlete.id,
            "success": True
        })
        set_access_cookies(resp, JWT)
        
        return resp, 200
    
    except Exception as e:
        print({'type': 'ERROR', 'message': str(e)})
        return jsonify({"error": "Failed to authenticate"}), 500
    
@app.route('/auth/logout', methods=['POST'])
def logout_with_cookies():
    response = jsonify({"msg": "logout successful"})
    unset_jwt_cookies(response)
    return response
    
@app.route('/auth/whoami', methods=['GET'])
@jwt_required()
def who_am_i():
    try:
        user = get_jwt_identity()
        athlete = db.get_athlete_by_id(user["id"])
        
        if not athlete:
            return jsonify({"error": "User not found in database"}), 404
        
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
        print({'type': 'ERROR', 'message': str(e)})
        return jsonify({"error": "Failed to fetch user information"}), 500

##############
# ACTIVITIES #
##############
@app.route('/activities', methods=['GET'])
@jwt_required()
def get_activities():
    try:
        after = request.args.get('after')
        before = request.args.get('before')
        
        if before is None or after is None:
            return jsonify({"msg": "Missing start or end date in request"}), 400
        
        user = get_jwt_identity()
        athlete = db.get_athlete_by_id(user["id"])
        
        if not athlete:
            return jsonify({"error": "User not found in database"}), 404
        
        # Fetch activities from Strava API
        client = Client(access_token=athlete['access_token'])
        
        # convert dates to datetime objects
        if isinstance(after, str):
            after_dt = datetime.fromisoformat(after.replace('Z', '+00:00'))
        else:
            after_dt = after
            
        if isinstance(before, str):
            before_dt = datetime.fromisoformat(before.replace('Z', '+00:00'))
        else:
            before_dt = before
        
        activities = client.get_activities(after=after_dt, before=before_dt)
        
        # Convert activities to JSON-serializable format
        activities_list = []
        for activity in activities:
            activity_dict = dict(activity)
            
            for key, value in activity_dict.items():
                if isinstance(value, datetime):
                    activity_dict[key] = value.isoformat()
                elif isinstance(value, timedelta):
                    activity_dict[key] = value.total_seconds()
                elif hasattr(value, '__dict__') and not isinstance(value, (str, int, float, bool, type(None))):
                    activity_dict[key] = str(value)
            
            activities_list.append(activity_dict)
        
        return jsonify({
            "activities": activities_list,
            "count": len(activities_list),
            "success": True
        }), 200
    
    except Exception as e:
        print({'type': 'ERROR', 'message': str(e)})
        return jsonify({"error": f"Failed to fetch activities: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(port=3011, debug=True)
