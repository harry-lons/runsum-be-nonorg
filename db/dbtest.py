import oracledb
import os
from dotenv import load_dotenv

# simple script to test connection to the database

# Load .env from parent directory
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)

# Get database credentials from environment variables
username = os.getenv('ORACLE_USER', 'ADMIN')  # Default to ADMIN, or set via env var
password = os.getenv('ORACLE_PASSWORD')  # Must be set as environment variable

# Path to wallet directory (in parent directory)
wallet_location = os.path.join(os.path.dirname(__file__), '..', 'wallet')
wallet_password = os.getenv('WALLET_PASSWORD')
# TNS name from tnsnames.ora (choose based on your needs)
# Options: runsum_high, runsum_medium, runsum_low, runsum_tp, runsum_tpurgent
dsn = "runsum_high"

try:
    # Connect using thin mode with wallet
    connection = oracledb.connect(
        user=username,
        password=password,
        dsn=dsn,
        config_dir=wallet_location,
        wallet_location=wallet_location,
        wallet_password=wallet_password
    )
    
    print("Successfully connected to Oracle Autonomous Database!")
    print(f"Database version: {connection.version}")
    
    # Test query
    cursor = connection.cursor()
    cursor.execute("SELECT 'Hello from Oracle!' as message FROM dual")
    result = cursor.fetchone()
    print(f"Query result: {result[0]}")
    
    cursor.close()
    connection.close()
    print("Connection closed successfully.")
    
except oracledb.Error as error:
    print(f"Error connecting to database: {error}")
except Exception as e:
    print(f"Unexpected error: {e}")
