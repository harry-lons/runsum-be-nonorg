import oracledb
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Database credentials
username = os.getenv('ORACLE_USER', 'ADMIN')
password = os.getenv('ORACLE_PASSWORD')

# Check if running on Render (they provide RENDER env var)
if os.getenv('RENDER'):
    # On Render, wallet files are uploaded as Secret Files
    wallet_location = '/etc/secrets'
else:
    # Local development - wallet_location is in the parent directory (project root)
    wallet_location = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'wallet')

wallet_password = os.getenv('WALLET_PASSWORD', '')
dsn = "runsum_high"

def get_db_connection():
    """Create and return a database connection"""
    try:
        connection = oracledb.connect(
            user=username,
            password=password,
            dsn=dsn,
            config_dir=wallet_location,
            wallet_location=wallet_location,
            wallet_password=wallet_password
        )
        return connection
    except oracledb.Error as error:
        print(f"Error connecting to database: {error}")
        raise

def get_athlete_by_id(strava_athlete_id):
    """Fetch athlete data from database by Strava ID"""
    connection = get_db_connection()
    cursor = connection.cursor()
    
    try:
        cursor.execute("""
            SELECT StravaAthleteID, firstname, lastname, firstlogin, lastlogin, 
                   access_token, ref_token, exp_at
            FROM athlete
            WHERE StravaAthleteID = :id
        """, [strava_athlete_id])
        
        result = cursor.fetchone()
        
        if result:
            return {
                'strava_id': result[0],
                'firstname': result[1],
                'lastname': result[2],
                'firstlogin': result[3],
                'lastlogin': result[4],
                'access_token': result[5],
                'refresh_token': result[6],
                'expires_at': result[7]
            }
        return None
    finally:
        cursor.close()
        connection.close()

def create_athlete(strava_athlete_id, firstname, lastname, access_token, refresh_token, expires_at):
    """Insert new athlete into database"""
    connection = get_db_connection()
    cursor = connection.cursor()
    
    try:
        now = datetime.now()
        cursor.execute("""
            INSERT INTO athlete 
            (StravaAthleteID, firstname, lastname, firstlogin, lastlogin, 
             access_token, ref_token, exp_at)
            VALUES (:id, :firstname, :lastname, :firstlogin, :lastlogin, 
                    :access_token, :ref_token, :exp_at)
        """, [strava_athlete_id, firstname, lastname, now, now, 
              access_token, refresh_token, expires_at])
        
        connection.commit()
        return True
    except oracledb.Error as error:
        print(f"Error creating athlete: {error}")
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()

def update_athlete_tokens(strava_athlete_id, access_token, refresh_token, expires_at):
    """Update athlete's Strava tokens"""
    connection = get_db_connection()
    cursor = connection.cursor()
    
    try:
        now = datetime.now()
        cursor.execute("""
            UPDATE athlete
            SET access_token = :access_token,
                ref_token = :ref_token,
                exp_at = :exp_at,
                lastlogin = :lastlogin
            WHERE StravaAthleteID = :id
        """, [access_token, refresh_token, expires_at, now, strava_athlete_id])
        
        connection.commit()
        return True
    except oracledb.Error as error:
        print(f"Error updating athlete tokens: {error}")
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()

def update_athlete_name(strava_athlete_id, firstname, lastname):
    """Update athlete's name (in case they changed it on Strava)"""
    connection = get_db_connection()
    cursor = connection.cursor()
    
    try:
        cursor.execute("""
            UPDATE athlete
            SET firstname = :firstname,
                lastname = :lastname
            WHERE StravaAthleteID = :id
        """, [firstname, lastname, strava_athlete_id])
        
        connection.commit()
        return True
    except oracledb.Error as error:
        print(f"Error updating athlete name: {error}")
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


