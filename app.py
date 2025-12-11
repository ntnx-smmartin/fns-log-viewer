from flask import Flask, render_template, request, jsonify
import pymysql
from datetime import datetime, timedelta
import pytz
from app_config import *

app = Flask(__name__)

def get_db_connection():
    """Create and return a database connection"""
    return pymysql.connect(**DB_CONFIG)

def convert_timezone(dt_str, target_tz):
    """Convert UTC datetime string to target timezone"""
    if not dt_str:
        return dt_str
    try:
        # Parse the datetime string
        dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
        # Assume it's UTC
        dt_utc = pytz.utc.localize(dt)
        # Convert to target timezone
        target_timezone = pytz.timezone(target_tz)
        dt_target = dt_utc.astimezone(target_timezone)
        return dt_target.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        print(f"Timezone conversion error: {e}, dt_str={dt_str}, target_tz={target_tz}")
        return dt_str

@app.route('/')
def index():
    """Main page with the logs table"""
    # Curated list of common timezones (one per UTC offset)
    common_timezones = [
        'UTC',
        'US/Pacific',
        'US/Mountain',
        'US/Central',
        'US/Eastern',
        'America/Caracas',
        'America/Santiago',
        'America/Sao_Paulo',
        'Atlantic/Cape_Verde',
        'Europe/London',
        'Europe/Paris',
        'Europe/Athens',
        'Africa/Nairobi',
        'Asia/Dubai',
        'Asia/Karachi',
        'Asia/Kolkata',
        'Asia/Dhaka',
        'Asia/Bangkok',
        'Asia/Hong_Kong',
        'Asia/Tokyo',
        'Australia/Sydney',
        'Pacific/Auckland'
    ]
    return render_template('index.html', timezones=common_timezones)

@app.route('/analytics')
def analytics():
    """Analytics page with traffic graphs"""
    # Curated list of common timezones (one per UTC offset)
    common_timezones = [
        'UTC',
        'US/Pacific',
        'US/Mountain',
        'US/Central',
        'US/Eastern',
        'America/Caracas',
        'America/Santiago',
        'America/Sao_Paulo',
        'Atlantic/Cape_Verde',
        'Europe/London',
        'Europe/Paris',
        'Europe/Athens',
        'Africa/Nairobi',
        'Asia/Dubai',
        'Asia/Karachi',
        'Asia/Kolkata',
        'Asia/Dhaka',
        'Asia/Bangkok',
        'Asia/Hong_Kong',
        'Asia/Tokyo',
        'Australia/Sydney',
        'Pacific/Auckland'
    ]
    return render_template('analytics.html', timezones=common_timezones)

@app.route('/statistics')
def statistics():
    """Statistics page with database metrics"""
    return render_template('statistics.html')

@app.route('/api/logs')
def get_logs():
    """API endpoint to fetch logs with filtering and sorting"""
    # Get query parameters
    sort_by = request.args.get('sort', 'received_timestamp')
    sort_order = request.args.get('order', 'DESC')
    
    # Filtering parameters - using parameterized queries to prevent SQL injection
    hostname_filter = request.args.get('hostname', '').strip()
    source_filter = request.args.get('source', '').strip()
    destination_filter = request.args.get('destination', '').strip()
    action_filter = request.args.get('action', '').strip()
    protocol_filter = request.args.get('protocol', '').strip()
    rule_name_filter = request.args.get('rule_name', '').strip()
    start_time = request.args.get('start_time', '').strip()
    end_time = request.args.get('end_time', '').strip()
    
    # Timezone for conversion
    target_tz = request.args.get('timezone', 'UTC')
    
    # Pagination - validate inputs to prevent division by zero and invalid values
    try:
        page = int(request.args.get('page', 1))
        if page < 1:
            page = 1
    except (ValueError, TypeError):
        page = 1
    
    try:
        per_page = int(request.args.get('per_page', 100))
        if per_page < 1:
            per_page = 100  # Default to 100 if invalid value provided
    except (ValueError, TypeError):
        per_page = 100
    
    offset = (page - 1) * per_page
    
    # Valid columns for sorting (prevent SQL injection)
    valid_columns = [
        'id', 'received_timestamp', 'hostname', 'os', 'event_timestamp',
        'rule_uuid', 'rule_name', 'event_type', 'source', 'destination',
        'protocol', 'source_port', 'destination_port', 'action', 'direction',
        'originator_packets', 'originator_bytes', 'reply_packets', 'reply_bytes'
    ]
    
    if sort_by not in valid_columns:
        sort_by = 'received_timestamp'
    
    if sort_order.upper() not in ['ASC', 'DESC']:
        sort_order = 'DESC'
    
    # Build WHERE clause with parameterized queries
    where_clauses = []
    params = []
    
    if hostname_filter:
        where_clauses.append("hostname LIKE %s")
        params.append(f"%{hostname_filter}%")
    
    if source_filter:
        where_clauses.append("source LIKE %s")
        params.append(f"%{source_filter}%")
    
    if destination_filter:
        where_clauses.append("destination LIKE %s")
        params.append(f"%{destination_filter}%")
    
    if action_filter:
        where_clauses.append("action = %s")
        params.append(action_filter)
    
    if protocol_filter:
        where_clauses.append("protocol = %s")
        params.append(protocol_filter)
    
    if rule_name_filter:
        where_clauses.append("rule_name LIKE %s")
        params.append(f"%{rule_name_filter}%")
    
    if start_time:
        where_clauses.append("received_timestamp >= %s")
        params.append(start_time)
    
    if end_time:
        where_clauses.append("received_timestamp <= %s")
        params.append(end_time)
    
    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)
    
    # Query database
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Get total count
            count_sql = f"SELECT COUNT(*) as total FROM fns_logs {where_sql}"
            cursor.execute(count_sql, params)
            total = cursor.fetchone()['total']
            
            # Get logs
            sql = f"""
                SELECT * FROM fns_logs 
                {where_sql}
                ORDER BY {sort_by} {sort_order}
                LIMIT %s OFFSET %s
            """
            cursor.execute(sql, params + [per_page, offset])
            logs = cursor.fetchall()
            
            # Convert datetime objects to strings and apply timezone conversion
            for log in logs:
                for key, value in log.items():
                    if isinstance(value, datetime):
                        dt_str = value.strftime('%Y-%m-%d %H:%M:%S')
                        # Convert timezone for timestamp fields
                        if key in ['received_timestamp', 'event_timestamp']:
                            log[key] = convert_timezone(dt_str, target_tz)
                        else:
                            log[key] = dt_str
            
            return jsonify({
                'logs': logs,
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': (total + per_page - 1) // per_page
            })
    finally:
        conn.close()

@app.route('/api/filter_options')
def get_filter_options():
    """Get distinct values for filter dropdowns"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            options = {}
            
            # Get distinct hostnames
            cursor.execute("SELECT DISTINCT hostname FROM fns_logs ORDER BY hostname")
            options['hostnames'] = [row['hostname'] for row in cursor.fetchall()]
            
            # Get distinct actions
            cursor.execute("SELECT DISTINCT action FROM fns_logs ORDER BY action")
            options['actions'] = [row['action'] for row in cursor.fetchall()]
            
            # Get distinct protocols
            cursor.execute("SELECT DISTINCT protocol FROM fns_logs ORDER BY protocol")
            options['protocols'] = [row['protocol'] for row in cursor.fetchall()]
            
            # Get distinct rule names
            cursor.execute("SELECT DISTINCT rule_name FROM fns_logs ORDER BY rule_name")
            options['rule_names'] = [row['rule_name'] for row in cursor.fetchall()]
            
            return jsonify(options)
    finally:
        conn.close()

@app.route('/api/analytics/by_source')
def analytics_by_source():
    """Get traffic statistics by source IP"""
    limit = int(request.args.get('limit', 10))
    start_time = request.args.get('start_time', '').strip()
    end_time = request.args.get('end_time', '').strip()
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            where_clauses = ["event_type = 'Destroy'"]
            params = []
            
            if start_time:
                where_clauses.append("received_timestamp >= %s")
                params.append(start_time)
            
            if end_time:
                where_clauses.append("received_timestamp <= %s")
                params.append(end_time)
            
            where_sql = "WHERE " + " AND ".join(where_clauses)
            
            sql = f"""
                SELECT source, 
                       SUM(originator_bytes + reply_bytes) as total_bytes,
                       COUNT(*) as connection_count
                FROM fns_logs
                {where_sql}
                GROUP BY source
                ORDER BY total_bytes DESC
                LIMIT %s
            """
            cursor.execute(sql, params + [limit])
            results = cursor.fetchall()
            return jsonify(results)
    finally:
        conn.close()

@app.route('/api/analytics/by_destination')
def analytics_by_destination():
    """Get traffic statistics by destination IP"""
    limit = int(request.args.get('limit', 10))
    start_time = request.args.get('start_time', '').strip()
    end_time = request.args.get('end_time', '').strip()
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            where_clauses = ["event_type = 'Destroy'"]
            params = []
            
            if start_time:
                where_clauses.append("received_timestamp >= %s")
                params.append(start_time)
            
            if end_time:
                where_clauses.append("received_timestamp <= %s")
                params.append(end_time)
            
            where_sql = "WHERE " + " AND ".join(where_clauses)
            
            sql = f"""
                SELECT destination, 
                       SUM(originator_bytes + reply_bytes) as total_bytes,
                       COUNT(*) as connection_count
                FROM fns_logs
                {where_sql}
                GROUP BY destination
                ORDER BY total_bytes DESC
                LIMIT %s
            """
            cursor.execute(sql, params + [limit])
            results = cursor.fetchall()
            return jsonify(results)
    finally:
        conn.close()

@app.route('/api/analytics/by_port')
def analytics_by_port():
    """Get traffic statistics by destination port"""
    limit = int(request.args.get('limit', 10))
    start_time = request.args.get('start_time', '').strip()
    end_time = request.args.get('end_time', '').strip()
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            where_clauses = ["event_type = 'Destroy'"]
            params = []
            
            if start_time:
                where_clauses.append("received_timestamp >= %s")
                params.append(start_time)
            
            if end_time:
                where_clauses.append("received_timestamp <= %s")
                params.append(end_time)
            
            where_sql = "WHERE " + " AND ".join(where_clauses)
            
            sql = f"""
                SELECT destination_port, 
                       SUM(originator_bytes + reply_bytes) as total_bytes,
                       COUNT(*) as connection_count
                FROM fns_logs
                {where_sql}
                GROUP BY destination_port
                ORDER BY total_bytes DESC
                LIMIT %s
            """
            cursor.execute(sql, params + [limit])
            results = cursor.fetchall()
            return jsonify(results)
    finally:
        conn.close()

@app.route('/api/analytics/by_rule')
def analytics_by_rule():
    """Get traffic statistics by rule name"""
    limit = int(request.args.get('limit', 10))
    start_time = request.args.get('start_time', '').strip()
    end_time = request.args.get('end_time', '').strip()
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            where_clauses = ["event_type = 'Destroy'"]
            params = []
            
            if start_time:
                where_clauses.append("received_timestamp >= %s")
                params.append(start_time)
            
            if end_time:
                where_clauses.append("received_timestamp <= %s")
                params.append(end_time)
            
            where_sql = "WHERE " + " AND ".join(where_clauses)
            
            sql = f"""
                SELECT rule_name, 
                       SUM(originator_bytes + reply_bytes) as total_bytes,
                       COUNT(*) as connection_count
                FROM fns_logs
                {where_sql}
                GROUP BY rule_name
                ORDER BY total_bytes DESC
                LIMIT %s
            """
            cursor.execute(sql, params + [limit])
            results = cursor.fetchall()
            return jsonify(results)
    finally:
        conn.close()

@app.route('/api/statistics')
def get_statistics():
    """Get database statistics including size and average records per time period"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            stats = {}
            
            # Get retention period
            retention_days = APP_CONFIG['days_to_keep_logs']
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            cutoff_date_str = cutoff_date.strftime('%Y-%m-%d %H:%M:%S')
            
            # Get database size
            cursor.execute("""
                SELECT 
                    table_schema AS 'Database',
                    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size_MB'
                FROM information_schema.TABLES 
                WHERE table_schema = %s
                GROUP BY table_schema
            """, (DB_CONFIG['database'],))
            db_size_result = cursor.fetchone()
            stats['database_size_mb'] = db_size_result['Size_MB'] if db_size_result else 0
            
            # Get table size specifically
            cursor.execute("""
                SELECT 
                    ROUND((data_length + index_length) / 1024 / 1024, 2) AS 'Size_MB',
                    table_rows AS 'Rows'
                FROM information_schema.TABLES 
                WHERE table_schema = %s AND table_name = 'fns_logs'
            """, (DB_CONFIG['database'],))
            table_size_result = cursor.fetchone()
            stats['table_size_mb'] = table_size_result['Size_MB'] if table_size_result else 0
            stats['table_rows'] = table_size_result['Rows'] if table_size_result else 0
            
            # Get total record count (within retention period)
            cursor.execute("""
                SELECT COUNT(*) as total 
                FROM fns_logs 
                WHERE received_timestamp >= %s
            """, (cutoff_date_str,))
            stats['total_records'] = cursor.fetchone()['total']
            
            # Get oldest and newest timestamps
            cursor.execute("""
                SELECT 
                    MIN(received_timestamp) as oldest,
                    MAX(received_timestamp) as newest
                FROM fns_logs
                WHERE received_timestamp >= %s
            """, (cutoff_date_str,))
            time_range = cursor.fetchone()
            stats['oldest_timestamp'] = time_range['oldest'].strftime('%Y-%m-%d %H:%M:%S') if time_range['oldest'] else None
            stats['newest_timestamp'] = time_range['newest'].strftime('%Y-%m-%d %H:%M:%S') if time_range['newest'] else None
            
            # Calculate average records per time period (only for data within retention period)
            now = datetime.utcnow()
            cutoff_datetime = datetime.strptime(cutoff_date_str, '%Y-%m-%d %H:%M:%S')
            
            # Average per minute (last hour)
            hour_ago = now - timedelta(hours=1)
            # Use the more recent of the two dates (retention cutoff or time period start)
            period_start = max(cutoff_datetime, hour_ago)
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM fns_logs 
                WHERE received_timestamp >= %s
            """, (period_start.strftime('%Y-%m-%d %H:%M:%S'),))
            hour_count = cursor.fetchone()['count']
            stats['avg_per_minute'] = round(hour_count / 60.0, 2) if hour_count > 0 else 0
            
            # Average per hour (last 24 hours)
            day_ago = now - timedelta(days=1)
            # Use the more recent of the two dates (retention cutoff or time period start)
            period_start = max(cutoff_datetime, day_ago)
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM fns_logs 
                WHERE received_timestamp >= %s
            """, (period_start.strftime('%Y-%m-%d %H:%M:%S'),))
            day_count = cursor.fetchone()['count']
            stats['avg_per_hour'] = round(day_count / 24.0, 2) if day_count > 0 else 0
            
            # Average per day (last 7 days, but not exceeding retention period)
            week_days = min(7, retention_days)
            week_ago = now - timedelta(days=week_days)
            # Use the more recent of the two dates (retention cutoff or time period start)
            period_start = max(cutoff_datetime, week_ago)
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM fns_logs 
                WHERE received_timestamp >= %s
            """, (period_start.strftime('%Y-%m-%d %H:%M:%S'),))
            week_count = cursor.fetchone()['count']
            stats['avg_per_day'] = round(week_count / float(week_days), 2) if week_count > 0 else 0
            
            # Average per week (last 4 weeks, but not exceeding retention period)
            month_weeks = min(4, retention_days // 7)
            if month_weeks > 0:
                month_weeks_ago = now - timedelta(weeks=month_weeks)
                # Use the more recent of the two dates (retention cutoff or time period start)
                period_start = max(cutoff_datetime, month_weeks_ago)
                cursor.execute("""
                    SELECT COUNT(*) as count 
                    FROM fns_logs 
                    WHERE received_timestamp >= %s
                """, (period_start.strftime('%Y-%m-%d %H:%M:%S'),))
                month_weeks_count = cursor.fetchone()['count']
                stats['avg_per_week'] = round(month_weeks_count / float(month_weeks), 2) if month_weeks_count > 0 else 0
            else:
                stats['avg_per_week'] = 0
            
            # Average per month (entire retention period, but not exceeding retention period)
            retention_weeks = retention_days / 7.0
            retention_months = retention_weeks / 4.0
            if retention_months > 0:
                stats['avg_per_month'] = round(stats['total_records'] / retention_months, 2) if stats['total_records'] > 0 else 0
            else:
                stats['avg_per_month'] = 0
            
            # Add retention period info
            stats['retention_days'] = retention_days
            stats['cutoff_date'] = cutoff_date_str
            
            return jsonify(stats)
    except Exception as e:
        # Log the error and return a proper error response
        import traceback
        print(f"Error in get_statistics: {e}")
        traceback.print_exc()
        return jsonify({
            'error': str(e),
            'database_size_mb': 0,
            'table_size_mb': 0,
            'total_records': 0,
            'avg_per_minute': 0,
            'avg_per_hour': 0,
            'avg_per_day': 0,
            'avg_per_week': 0,
            'avg_per_month': 0,
            'retention_days': APP_CONFIG.get('days_to_keep_logs', 30),
            'cutoff_date': None,
            'oldest_timestamp': None,
            'newest_timestamp': None,
            'table_rows': 0
        }), 500
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)