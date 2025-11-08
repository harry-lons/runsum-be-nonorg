# Oracle Database Integration - Changes Summary

## Overview
The backend has been updated to use Oracle Autonomous Database for storing athlete data and Strava credentials. JWT tokens are still used for frontend-backend authentication, but Strava tokens are now securely stored in the database.

## New Files Created

### 1. `db_utils.py`
Database utility module with functions for:
- `get_db_connection()` - Creates database connections
- `get_athlete_by_id()` - Fetch athlete from DB
- `create_athlete()` - Insert new athlete
- `update_athlete_tokens()` - Update Strava tokens
- `update_athlete_name()` - Update athlete name

### 2. `test_auth_flow.py`
Comprehensive test script that tests:
- Login endpoint (creates/updates DB records)
- Whoami endpoint (reads from DB)
- Activities endpoint (uses tokens from DB)
- Logout endpoint

### 3. `TESTING_GUIDE.md`
Complete documentation covering:
- Setup instructions
- Testing procedures
- API endpoint details
- Troubleshooting guide

## Modified Files

### 1. `main.py`
**Changes:**
- Added `import db_utils as db`
- Updated `/auth/login` route:
  - Now stores athlete data in database
  - Creates new records for first-time users
  - Updates tokens for returning users
- Updated `/auth/whoami` route:
  - Fetches user data from database instead of just JWT
- Updated `/activities` route:
  - Added `@jwt_required()` decorator
  - Fetches Strava tokens from database
  - Uses stored tokens to create Strava client
  - Fetches and returns activities from Strava API

### 2. `helpers.py`
**Changes:**
- Updated `get_token_from_code()` to return three values:
  - `access_token`
  - `refresh_token`
  - `expires_at` (datetime object)

## Database Schema

The database schema is defined in `db/schemas.sql`. Create the table using your SQL editor:

```sql
CREATE TABLE athlete (
  StravaAthleteID NUMBER(19) NOT NULL PRIMARY KEY,
  firstname VARCHAR2(255),
  lastname VARCHAR2(255),
  firstlogin TIMESTAMP,
  lastlogin TIMESTAMP,
  access_token VARCHAR2(255),
  ref_token VARCHAR2(255),
  exp_at TIMESTAMP
);
```

## Authentication Flow

### Before (Old Flow)
```
User → Strava OAuth → Backend exchanges code for tokens
     → Backend creates JWT with tokens embedded
     → JWT sent to frontend
     → Frontend sends JWT with each request
     → Backend extracts tokens from JWT to call Strava API
```

### After (New Flow)
```
User → Strava OAuth → Backend exchanges code for tokens
     → Backend stores tokens in Oracle database
     → Backend creates JWT with only user ID
     → JWT sent to frontend
     → Frontend sends JWT with each request
     → Backend extracts user ID from JWT
     → Backend fetches tokens from database
     → Backend uses tokens to call Strava API
```

## Benefits

1. **Security**: Strava tokens stored securely in database, not in JWT
2. **Scalability**: Can implement token refresh without frontend involvement
3. **Persistence**: User data persists across sessions
4. **Flexibility**: Easy to add more user data/preferences to database
5. **Audit Trail**: Track first login and last login timestamps

## Testing Instructions

### Quick Test
```bash
# 1. Ensure athlete table exists in database (run schemas.sql in your SQL editor)

# 2. Test database connection
cd db
python dbtest.py

# 3. Start backend
cd ..
python main.py

# 4. Get Strava auth code from:
# https://www.strava.com/oauth/authorize?client_id=YOUR_CLIENT_ID&response_type=code&redirect_uri=http://localhost&approval_prompt=force&scope=read,activity:read_all

# 5. Update tests/test_auth_flow.py with your code and run:
cd tests
python test_auth_flow.py
```

See `TESTING_GUIDE.md` for detailed instructions.

## Environment Variables Required

```bash
# Strava
CLIENT_ID=your_strava_client_id
CLIENT_SECRET=your_strava_client_secret

# Oracle Database
ORACLE_USER=ADMIN
ORACLE_PASSWORD=your_oracle_password
WALLET_PASSWORD=  # Usually empty for Autonomous DB

# App
FRONTEND_URL=http://localhost:3000
SECURE=false  # Set to true in production
JWT_SECRET=your_jwt_secret
```

## Next Steps / TODO

1. **Implement Token Refresh**: Automatically refresh Strava tokens when they expire
2. **Add Activity Caching**: Store activities in database to reduce API calls
3. **Rate Limiting**: Implement rate limiting for Strava API calls
4. **Error Handling**: Better handling of token expiration scenarios
5. **Logging**: Add structured logging for debugging
6. **Database Migrations**: Set up a migration system for schema changes

## Troubleshooting

### "Error connecting to database"
- Check `.env` file has correct `ORACLE_PASSWORD`
- Verify wallet files are in `wallet/` directory
- Ensure wallet hasn't expired (check `wallet/README`)

### "User not found in database"
- User must authenticate via `/auth/login` first
- Ensure the athlete table exists in the database

### "Failed to authenticate"
- Strava auth codes expire in ~10 minutes
- Get a fresh code and try again
- Verify `CLIENT_ID` and `CLIENT_SECRET` in `.env`

## Questions?

Refer to `TESTING_GUIDE.md` for comprehensive documentation, or check the inline comments in each file.


