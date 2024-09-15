from flask import Flask, request, jsonify, make_response
from dotenv import load_dotenv
from stravalib import Client
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
import os
from flask_cors import CORS
from datetime import timedelta

load_dotenv()
CLIENT_ID=os.getenv('CLIENT_ID')
CLIENT_SECRET=os.getenv('CLIENT_SECRET')
app = Flask(__name__)

cors = CORS(app, resources={r"/*": {"origins": os.getenv('FRONTEND_URL')}}, supports_credentials=True)

app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=15)

client = Client()

@app.route("/")
def home():
    return "Hello HTTPS!"

@app.route("/get-token", methods=["POST"])
def getTokenFromCode():
    data = request.get_json()
    code = data['code']
    try:
        token_response = client.exchange_code_for_token(CLIENT_ID,
                                                        CLIENT_SECRET,
                                                        code=code)
    except Exception as e:
        return {'type':'ERROR', 'message': str(e)}, 500
    
    if 'access_token' in token_response and 'refresh_token' in token_response:
        resp = make_response(jsonify({"access_token": token_response['access_token']}))
        resp.set_cookie('refresh_token', token_response['refresh_token'], httponly=True, secure=os.getenv('SECURE'), samesite='Lax')

        return resp, 200
    else:
        return jsonify({"error": "Failed to exchange token"}), 400
    
@app.route('/refresh-token', methods=['POST'])
def refresh_access_token():
    # Get refresh token from HttpOnly cookie
    refresh_token = request.cookies.get('refresh_token')
    if not refresh_token:
        return jsonify({"error": "No refresh token"}), 450

    # Request new access token from Strava
    token_data = client.refresh_access_token(CLIENT_ID, CLIENT_SECRET, refresh_token)
    
    if 'access_token' in token_data:
        new_access_token = token_data['access_token']
        # Return new access token to the frontend
        return jsonify({"access_token": new_access_token})
    else:
        return jsonify({"error": "Failed to refresh access token"}), 400


if __name__ == "__main__":
    app.run(debug=True, port=3011)
