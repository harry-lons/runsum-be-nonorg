from flask import Flask, request, jsonify
from dotenv import load_dotenv
from stravalib import Client
import os
import ssl
from flask_cors import CORS

load_dotenv()
app = Flask(__name__)
cors = CORS(app, resources={r"/*": {"origins": os.getenv('FRONTEND_URL')}})

@app.route("/")
def home():
    return "Hello HTTPS!"

@app.route("/get-token", methods=["POST"])
def getToken():
    data = request.get_json()
    code = data['code']
    client = Client()
    try:
        token_response = client.exchange_code_for_token(client_id=os.getenv('CLIENT_ID'),
                                                        client_secret=os.getenv('CLIENT_SECRET'),
                                                        code=code)
    except Exception as e:
        return {'type':'ERROR', 'message': str(e)}, 500
    
    tokens = {
        'type': 'SUCCESS',
        'access_token': token_response['access_token'],
        'refresh_token': token_response['refresh_token'],
    }
    print(tokens)
    return jsonify(tokens), 200

if __name__ == "__main__":
    if os.getenv('SSL_CRT') and os.getenv('SSL_KEY'):
        context = ('localhost.crt', 'localhost.key')
        app.run(ssl_context=context, debug=True, port=3011)
    else:
        app.run(debug=True, port=3011)
