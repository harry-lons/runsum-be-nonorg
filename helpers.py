from stravalib import Client
from datetime import datetime

def get_token_from_code(auth_client, code, CLIENT_ID, CLIENT_SECRET):
    try:
        token_response = auth_client.exchange_code_for_token(
            CLIENT_ID, CLIENT_SECRET, code=code
        )
    except Exception as e:
        print({'type': 'ERROR', 'message': str(e)})
        return {'type': 'ERROR', 'message': str(e)}, 500

    if 'access_token' in token_response and 'refresh_token' in token_response:
        access_token = token_response['access_token']
        refresh_token = token_response['refresh_token']
        # expires_at is a Unix timestamp
        expires_at = datetime.fromtimestamp(token_response['expires_at']) if 'expires_at' in token_response else None
        return access_token, refresh_token, expires_at
    else:
        raise ValueError("Strava response missing tokens")
