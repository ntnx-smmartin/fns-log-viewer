import pymysql

APP_CONFIG = {
    'days_to_keep_logs': 30, # Number of days to keep logs in the database
    'default_timezone': 'UTC', # Default timezone for the app
}

DB_CONFIG = {
    'host': '127.0.0.1', # IP address or hostname of database server
    'user': 'rsyslog', # Username for database
    'password': '4u/Nutanix!', # Password for database
    'database': 'Syslog', # Database name
    'cursorclass': pymysql.cursors.DictCursor # Cursor class for database
}