from stravalib import Client
from datetime import datetime
from db import db_utils as db
import requests
import time

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
        # print("expires_at: ", expires_at)
        # print("access_token: ", access_token)
        # print("refresh_token: ", refresh_token)
        return access_token, refresh_token, expires_at
    else:
        raise ValueError("Strava response missing tokens")

def log_query(athlete_id, start_date, end_date):
    """Log an activities query to the database"""
    connection = db.get_db_connection()
    cursor = connection.cursor()
    
    try:
        now = datetime.now()
        cursor.execute("""
            INSERT INTO queries 
            (athlete_id, querytime, startdate, enddate)
            VALUES (:athlete_id, :querytime, :startdate, :enddate)
        """, [athlete_id, now, start_date, end_date])
        
        connection.commit()
        return True
    except Exception as error:
        print(f"Error logging query: {error}")
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def refresh_strava_token(refresh_token, CLIENT_ID, CLIENT_SECRET):
    """Refresh an expired Strava access token"""
    try:
        auth_client = Client()
        token_response = auth_client.refresh_access_token(
            CLIENT_ID, CLIENT_SECRET, refresh_token
        )
        
        access_token = token_response['access_token']
        new_refresh_token = token_response['refresh_token']
        expires_at = datetime.fromtimestamp(token_response['expires_at'])
        
        return access_token, new_refresh_token, expires_at
    except Exception as e:
        print(f"Error refreshing token: {e}")
        raise

# legacy function for fetching activities through stravalib
def get_valid_strava_client(athlete, CLIENT_ID, CLIENT_SECRET):
    # Get a Strava client with a valid access token, refreshing if needed
    
    # Check if token is expired or about to expire (within 5 minutes)
    now = datetime.now()
    expires_at = athlete['expires_at']
    
    if expires_at <= now:
        # Token is expired, refresh it
        new_access_token, new_refresh_token, new_expires_at = refresh_strava_token(
            athlete['refresh_token'], CLIENT_ID, CLIENT_SECRET
        )
        
        # Update database with new tokens
        db.update_athlete_tokens(
            athlete['strava_id'], 
            new_access_token, 
            new_refresh_token, 
            new_expires_at
        )
        
        return Client(access_token=new_access_token)
    else:
        # Token is still valid
        return Client(access_token=athlete['access_token'])


def fetch_activities(athlete, after_epoch, before_epoch):
    
    # Fetch activities from Strava API using raw HTTP requests
    all_activities = []
    page = 1
    has_more = True
    
    while has_more:
        # Add a cache-busting parameter using current timestamp
        nocache = int(time.time() * 1000)  # Current time in milliseconds
        
        # Make the API call
        url = f"https://www.strava.com/api/v3/athlete/activities?after={after_epoch}&before={before_epoch}&page={page}&per_page=200&nocache={nocache}"
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {athlete["access_token"]}'
        }
        print(athlete["access_token"])
        
        try:
            response = requests.get(url, headers=headers)
            
            # Check if the response is successful (status code 200-299)
            if not response.ok:
                print(f"Error: Response status {response.status_code}")
                raise Exception(f'Network response was not ok: {response.status_code}')
            
            # Parse the response body as JSON
            activities = response.json()
            
            # If there are activities in the response, add them to the allActivities array
            if len(activities) > 0:
                print(f"Fetched page {page} with {len(activities)} activities")
                all_activities.extend(activities)
                page += 1  # Increment the page number for the next request
            else:
                print("All activities fetched")
                has_more = False  # No more activities to fetch
                
        except Exception as e:
            print(f"Error fetching activities: {e}")
            raise
    
    return all_activities
