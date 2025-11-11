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

# TNS connection string for TLS (one-way) mode - no wallet needed
dsn = os.getenv('ORACLE_DSN')

try:
    # Connect using TLS (one-way) - no wallet needed
    connection = oracledb.connect(
        user=username,
        password=password,
        dsn=dsn
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
