#!/usr/bin/env python3
"""
Sample Data Generator for FNS Log Viewer

This script generates sample FNS log entries for testing purposes.
It creates realistic log data spread over the retention period.

Usage:
    python3 generate_sample_data.py [--days DAYS] [--records-per-day COUNT]
"""

import sys
import argparse
import random
import uuid
from datetime import datetime, timedelta
from app_config import DB_CONFIG

# Sample data pools
HOSTNAMES = ['ahv-host-1', 'ahv-host-2', 'ahv-host-3', 'ahv-host-4', 'nutanix-cluster-1']
OS_TYPES = ['ahv', 'esxi', 'hyperv']
RULE_NAMES = [
    'Default Global Policy',
    'Web Server Access',
    'Database Access',
    'Internal Network',
    'DMZ Access',
    'Block Malicious IPs',
    'Allow Outbound Internet via HTTP and HTTPS',
    'VPN Access Policy'
]
EVENT_TYPES = ['Create', 'Destroy']
PROTOCOLS = ['TCP', 'UDP', 'ICMP']
ACTIONS = ['ALLOW', 'DENY', 'REJECT']
DIRECTIONS = ['INBOUND', 'OUTBOUND']
COMMON_PORTS = [80, 443, 22, 23, 25, 53, 3306, 5432, 3389, 8080, 8443]
DESCRIPTIONS = [
    'Allow Outbound Internet via HTTP and HTTPS',
    'Block unauthorized access',
    'Internal network communication',
    'Database connection',
    'Web server traffic',
    None  # Some logs don't have descriptions
]


def generate_random_ip():
    """Generate a random IP address"""
    return f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"


def generate_sample_log(received_timestamp, event_timestamp):
    """Generate a single sample log entry"""
    rule_uuid = str(uuid.uuid4())
    rule_name = random.choice(RULE_NAMES)
    event_type = random.choice(EVENT_TYPES)
    protocol = random.choice(PROTOCOLS)
    action = random.choice(ACTIONS)
    direction = random.choice(DIRECTIONS)
    
    # Generate realistic port numbers
    if protocol == 'ICMP':
        source_port = 0
        destination_port = 0
    else:
        source_port = random.randint(1024, 65535)
        destination_port = random.choice(COMMON_PORTS) if random.random() > 0.3 else random.randint(1, 65535)
    
    # Generate realistic packet/byte counts
    if event_type == 'Destroy':
        # Destroy events have more realistic traffic
        originator_packets = random.randint(5, 1000)
        originator_bytes = random.randint(100, 1000000)
        reply_packets = random.randint(5, 1000)
        reply_bytes = random.randint(100, 1000000)
    else:
        # Create events typically have minimal traffic
        originator_packets = random.randint(1, 10)
        originator_bytes = random.randint(50, 500)
        reply_packets = random.randint(1, 10)
        reply_bytes = random.randint(50, 500)
    
    description = random.choice(DESCRIPTIONS)
    
    return {
        'received_timestamp': received_timestamp,
        'hostname': random.choice(HOSTNAMES),
        'os': random.choice(OS_TYPES),
        'event_timestamp': event_timestamp,
        'rule_uuid': rule_uuid,
        'rule_name': rule_name,
        'event_type': event_type,
        'source': generate_random_ip(),
        'destination': generate_random_ip(),
        'protocol': protocol,
        'source_port': source_port,
        'destination_port': destination_port,
        'action': action,
        'direction': direction,
        'originator_packets': originator_packets,
        'originator_bytes': originator_bytes,
        'reply_packets': reply_packets,
        'reply_bytes': reply_bytes,
        'description': description
    }


def insert_logs(conn, logs):
    """Insert logs into the database"""
    import pymysql
    
    sql = """
        INSERT INTO fns_logs (
            received_timestamp, hostname, os, event_timestamp, rule_uuid,
            rule_name, event_type, source, destination, protocol,
            source_port, destination_port, action, direction,
            originator_packets, originator_bytes, reply_packets, reply_bytes, description
        ) VALUES (
            %(received_timestamp)s, %(hostname)s, %(os)s, %(event_timestamp)s, %(rule_uuid)s,
            %(rule_name)s, %(event_type)s, %(source)s, %(destination)s, %(protocol)s,
            %(source_port)s, %(destination_port)s, %(action)s, %(direction)s,
            %(originator_packets)s, %(originator_bytes)s, %(reply_packets)s, %(reply_bytes)s, %(description)s
        )
    """
    
    with conn.cursor() as cursor:
        cursor.executemany(sql, logs)
    conn.commit()


def generate_sample_data(days, records_per_day):
    """Generate sample data for the specified number of days"""
    import pymysql
    
    print(f"Generating {records_per_day} records per day for {days} days...")
    print(f"Total records to generate: {days * records_per_day}")
    
    try:
        conn = pymysql.connect(**DB_CONFIG)
        print("Connected to database successfully")
    except Exception as e:
        print(f"Error connecting to database: {e}")
        print("Make sure the database exists and credentials in app_config.py are correct")
        sys.exit(1)
    
    try:
        # Check if table exists
        with conn.cursor() as cursor:
            cursor.execute("SHOW TABLES LIKE 'fns_logs'")
            if not cursor.fetchone():
                print("Error: fns_logs table does not exist!")
                print("Please create it using the SQL in conf/fns_logs.sql")
                sys.exit(1)
        
        # Generate data
        total_inserted = 0
        batch_size = 1000
        current_time = datetime.utcnow()
        
        for day in range(days):
            # Start from retention period days ago and work forward
            day_start = current_time - timedelta(days=days - day - 1)
            
            # Generate records for this day, spread throughout the day
            logs = []
            for record_num in range(records_per_day):
                # Spread records throughout the day
                hours_offset = (record_num / records_per_day) * 24
                record_time = day_start + timedelta(hours=hours_offset)
                
                # Event timestamp is slightly before received timestamp (typical syslog behavior)
                event_time = record_time - timedelta(seconds=random.randint(1, 10))
                
                log = generate_sample_log(record_time, event_time)
                logs.append(log)
                
                # Insert in batches
                if len(logs) >= batch_size:
                    insert_logs(conn, logs)
                    total_inserted += len(logs)
                    print(f"Inserted {total_inserted} records...", end='\r')
                    logs = []
            
            # Insert remaining logs for this day
            if logs:
                insert_logs(conn, logs)
                total_inserted += len(logs)
                print(f"Inserted {total_inserted} records...", end='\r')
        
        print(f"\nSuccessfully generated {total_inserted} sample log entries!")
        print(f"Data spans from {(current_time - timedelta(days=days-1)).strftime('%Y-%m-%d %H:%M:%S')} to {current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        
    except Exception as e:
        print(f"\nError generating data: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='Generate sample FNS log data for testing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate 30 days of data with 100 records per day
  python3 generate_sample_data.py --days 30 --records-per-day 100
  
  # Generate 7 days with 500 records per day
  python3 generate_sample_data.py --days 7 --records-per-day 500
        """
    )
    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days of data to generate (default: 30)'
    )
    parser.add_argument(
        '--records-per-day',
        type=int,
        default=100,
        help='Number of records to generate per day (default: 100)'
    )
    
    args = parser.parse_args()
    
    if args.days < 1:
        print("Error: days must be at least 1")
        sys.exit(1)
    
    if args.records_per_day < 1:
        print("Error: records-per-day must be at least 1")
        sys.exit(1)
    
    generate_sample_data(args.days, args.records_per_day)


if __name__ == '__main__':
    main()

