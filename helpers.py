
from stravalib import Client

def get_token_from_code(auth_client, code, CLIENT_ID, CLIENT_SECRET):
    try:
        token_response = auth_client.exchange_code_for_token(
            CLIENT_ID, CLIENT_SECRET, code=code
        )
    except Exception as e:
        print({'type': 'ERROR', 'message': str(e)})
        return {'type': 'ERROR', 'message': str(e)}, 500

    if 'access_token' in token_response and 'refresh_token' in token_response:
        return token_response['access_token'], token_response['refresh_token']
        return resp, 200
    else:
        raise ValueError("Strava response missing tokens")
