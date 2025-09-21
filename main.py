from flask import Flask, request, jsonify, make_response, g
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, set_access_cookies
from dotenv import load_dotenv
from stravalib import Client
from flask_cors import CORS
from datetime import datetime, timedelta
import helpers as h
import os

# Load environment variables
load_dotenv()
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
FRONTEND_URL = os.getenv('FRONTEND_URL')
SECURE = os.getenv('SECURE') == 'true'  # Convert 'true'/'false' to boolean
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
        # Exchange auth code for access and refresh tokens
        acc_tok, ref_tok = h.get_token_from_code(auth_client, code, CLIENT_ID=CLIENT_ID, CLIENT_SECRET=CLIENT_SECRET)
        # Create stravalib client with access token to fetch athlete info
        temp_client = Client(access_token=acc_tok)
        athlete = temp_client.get_athlete()

        athlete = temp_client.get_athlete() # Get user's full athlete record
        print("Hello, {}. I know your id is {}".format(athlete.firstname, athlete.id))

        # Create JWT token
        JWT = create_access_token(identity=athlete.id, expires_delta=timedelta(days=30))
        resp = jsonify({"first_name": athlete.firstname, "id": athlete.id, \
                        "success":True if athlete else ""})

        set_access_cookies(resp, JWT)
        
        # resp.set_cookie(
        #     'JWT',
        #     JWT,
        #     httponly=True,
        #     secure=SECURE,
        #     samesite='None' if SECURE else 'Lax',
        #     max_age=60*60*24*30  # 30 days
        # )
        # print(SECURE)
        return resp
    #     return resp, 200
    
    except Exception as e:
        print({'type': 'ERROR', 'message': str(e)})
        return jsonify({"error": "Failed to authenticate"}), 500
    
@app.route('/auth/logout', methods=['POST'])
def logout():
    # Get refresh token from HttpOnly cookie
    refresh_token = request.cookies.get('JWT')
    if not refresh_token:
        resp = make_response(
            jsonify({"success": 'no token to begin with (weird)'})
        )
        return resp, 200
    try:
        # Set the cookie to empty string
        resp = make_response(
            jsonify({"success": 'token removed successfully'})
        )
        resp.set_cookie(
            'JWT',
            '',
            httponly=True,
            secure=True,
            samesite='None',
            max_age=0       # Forces browser to immediately delete the cookie
        )
        return resp, 200
    except Exception as e:
        print({'type': 'ERROR', 'message': str(e)})
        return jsonify({"error": "Failed to logout (an unknown error occurred)"}), 500
    
@app.route('/auth/whoami', methods=['GET'])
@jwt_required()
def who_am_i():
    user = get_jwt_identity()
    # TODO: query database to figure out the user's real first name
    # Authenticate user
    resp = make_response(
            jsonify({"first_name": "FIRST NAME", "id": user, "success":True})
        )
    return resp, 200

##############
# ACTIVITIES #
##############
@app.route('/activities', methods=['GET'])
def get_activities():
    return jsonify({"message": "I am a placeholder!"}), 200

if __name__ == "__main__":
    app.run(port=3011, debug=True)
