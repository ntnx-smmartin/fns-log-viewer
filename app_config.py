import os
import pymysql

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not installed, user must set environment variables manually
    pass

APP_CONFIG = {
    'days_to_keep_logs': int(os.getenv('FNS_DAYS_TO_KEEP_LOGS', 30)), # Number of days to keep logs in the database
    'default_timezone': os.getenv('FNS_DEFAULT_TIMEZONE', 'UTC'), # Default timezone for the app
}

DB_CONFIG = {
    'host': os.getenv('FNS_DB_HOST', '127.0.0.1'), # IP address or hostname of database server
    'user': os.getenv('FNS_DB_USER', 'rsyslog'), # Username for database
    'password': os.getenv('FNS_DB_PASSWORD', ''), # Password for database (REQUIRED - set via environment variable)
    'database': os.getenv('FNS_DB_NAME', 'Syslog'), # Database name
    'cursorclass': pymysql.cursors.DictCursor # Cursor class for database
}

# Validate that required password is set
if not DB_CONFIG['password']:
    raise ValueError(
        "FNS_DB_PASSWORD environment variable is required but not set. "
        "Please set it before running the application. "
        "See README.md for configuration instructions."
    )