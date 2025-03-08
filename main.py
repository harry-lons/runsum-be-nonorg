from flask import Flask, request, jsonify, make_response
from dotenv import load_dotenv
from stravalib import Client
from flask_cors import CORS
from datetime import datetime, timedelta
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
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=15)

# Strava client
auth_client = Client()

@app.route("/")
def home():
    return "Hello HTTPS!"

@app.route("/get-token", methods=["POST"])
def get_token_from_code():
    data = request.get_json()
    code = data['code']

    try:
        token_response = auth_client.exchange_code_for_token(
            CLIENT_ID, CLIENT_SECRET, code=code
        )
    except Exception as e:
        print({'type': 'ERROR', 'message': str(e)})
        return {'type': 'ERROR', 'message': str(e)}, 500

    if 'access_token' in token_response and 'refresh_token' in token_response:
        # Set HttpOnly cookie for the refresh token
        resp = make_response(
            jsonify({"access_token": token_response['access_token']})
        )
        resp.set_cookie(
            'refresh_token',
            token_response['refresh_token'],
            httponly=True,
            secure=True,
            samesite='None'
        )
        return resp, 200
    else:
        return jsonify({"error": "Failed to exchange token"}), 400

@app.route('/refresh-token', methods=['POST'])
def refresh_access_token():
    # Get refresh token from HttpOnly cookie
    refresh_token = request.cookies.get('refresh_token')
    if not refresh_token:
        return jsonify({"error": "No refresh token"}), 403

    try:
        # Request a new access token from Strava
        token_data = auth_client.refresh_access_token(
            CLIENT_ID, CLIENT_SECRET, refresh_token
        )
    except Exception as e:
        print({'type': 'ERROR', 'message': str(e)})
        return jsonify({"error": "Failed to refresh access token"}), 500

    if 'access_token' in token_data:
        new_access_token = token_data['access_token']
        temp_client = Client(access_token=new_access_token)
        athlete = temp_client.get_athlete()
        first_name = athlete.firstname if athlete else ""
        # Return the new access token to the frontend
        return jsonify({"access_token": new_access_token, "first_name": first_name})
    else:
        return jsonify({"error": "Failed to refresh access token"}), 400
    
@app.route('/logout', methods=['POST'])
def logout():
    # Get refresh token from HttpOnly cookie
    refresh_token = request.cookies.get('refresh_token')
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
            'refresh_token',
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


if __name__ == "__main__":
    app.run(port=3011)
