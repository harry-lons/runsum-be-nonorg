"""
Test script for the full authentication flow with Oracle database integration.

Before running this test, change the auth_code. You will have to do some clever fandangling to actually get a code for yourself.
This is because the code is one-time-use
Typically I just do this by commenting out the callback function on my local version of the frontend so it doesnt get used,
and instead print the code to the console.

The test will:
- Authenticate using the code (creates/updates user in database)
- Verify whoami endpoint (reads from database)
- Fetch activities (uses stored tokens from database)
"""

import requests
from datetime import datetime, timedelta
import json

# Configuration
BASE_URL = "http://localhost:3011"
AUTH_CODE = "da5bf22b6d1853cf35a7f15ca9543120ebb5bf42"  # Replace with your actual auth code from Strava

# Date range for activities (last 30 days)
end_date = datetime.now()
start_date = end_date - timedelta(days=30)


def test_login():
    """Test the login endpoint"""
    print("\n" + "="*60)
    print("Testing /auth/login endpoint...")
    print("="*60)
    
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"code": AUTH_CODE},
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("✅ Login successful!")
        # Extract cookies for subsequent requests
        return response.cookies
    else:
        print("❌ Login failed!")
        return None


def test_whoami(cookies):
    """Test the whoami endpoint"""
    print("\n" + "="*60)
    print("Testing /auth/whoami endpoint...")
    print("="*60)
    
    response = requests.get(
        f"{BASE_URL}/auth/whoami",
        cookies=cookies
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("✅ Whoami successful! User data retrieved from database.")
    else:
        print("❌ Whoami failed!")
    
    return response.json() if response.status_code == 200 else None


def test_get_activities(cookies):
    """Test the get activities endpoint"""
    print("\n" + "="*60)
    print("Testing /activities endpoint...")
    print("="*60)
    
    # Format dates for API
    after_str = start_date.isoformat()
    before_str = end_date.isoformat()
    
    response = requests.get(
        f"{BASE_URL}/activities",
        params={
            "after": after_str,
            "before": before_str
        },
        cookies=cookies
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Activities fetched successfully!")
        print(f"Number of activities: {data.get('count', 0)}")
        
        # Print first few activities
        if data.get('activities'):
            print("\nFirst 3 activities:")
            for i, activity in enumerate(data['activities'][:3]):
                print(f"\n  Activity {i+1}:")
                print(f"    Name: {activity['name']}")
                print(f"    Type: {activity['type']}")
                print(f"    Distance: {activity['distance']:.2f} meters")
                print(f"    Date: {activity['start_date_local']}")
        
        return data
    else:
        print("❌ Failed to fetch activities!")
        print(f"Response: {response.text}")
        return None


def test_logout(cookies):
    """Test the logout endpoint"""
    print("\n" + "="*60)
    print("Testing /auth/logout endpoint...")
    print("="*60)
    
    response = requests.post(
        f"{BASE_URL}/auth/logout",
        cookies=cookies
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("✅ Logout successful!")
    else:
        print("❌ Logout failed!")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("STARTING FULL AUTHENTICATION FLOW TEST")
    print("="*60)
    print(f"Base URL: {BASE_URL}")
    print(f"Date Range: {start_date.date()} to {end_date.date()}")
    
    if AUTH_CODE == "YOUR_AUTH_CODE_HERE":
        print("\n❌ ERROR: Please replace AUTH_CODE with your actual Strava authorization code!")
        print("\nTo get an auth code, visit:")
        print("https://www.strava.com/oauth/authorize?client_id=YOUR_CLIENT_ID&response_type=code&redirect_uri=http://localhost&approval_prompt=force&scope=read,activity:read_all")
        return
    
    # Test 1: Login
    cookies = test_login()
    if not cookies:
        print("\n❌ Cannot continue testing - login failed")
        return
    
    # Test 2: Whoami
    user_data = test_whoami(cookies)
    
    # Test 3: Get Activities
    activities_data = test_get_activities(cookies)
    
    # Test 4: Logout
    test_logout(cookies)
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"✅ Login: {'Success' if cookies else 'Failed'}")
    print(f"✅ Whoami: {'Success' if user_data else 'Failed'}")
    print(f"✅ Get Activities: {'Success' if activities_data else 'Failed'}")
    print("\nAll tests completed!")
    print("="*60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


