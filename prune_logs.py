#!/usr/bin/env python3
"""
Log Pruning Script for FNS Log Viewer

This script removes log entries older than the configured retention period
from the fns_logs table. It should be run periodically via cron or systemd timer.

Usage:
    python3 prune_logs.py [--dry-run] [--days DAYS]

Options:
    --dry-run    Show what would be deleted without actually deleting
    --days DAYS  Override the retention period from app_config (default: use app_config)
"""

import sys
import argparse
import logging
from datetime import datetime, timedelta
from app_config import DB_CONFIG, APP_CONFIG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/fns-log-pruner.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def get_db_connection():
    """Create and return a database connection"""
    import pymysql
    return pymysql.connect(**DB_CONFIG)


def prune_logs(days_to_keep, dry_run=False):
    """
    Prune logs older than the specified number of days.
    
    Args:
        days_to_keep: Number of days of logs to retain
        dry_run: If True, only show what would be deleted without deleting
    
    Returns:
        tuple: (rows_deleted, cutoff_date)
    """
    conn = None
    try:
        conn = get_db_connection()
        
        # Calculate cutoff date (logs older than this will be deleted)
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        cutoff_date_str = cutoff_date.strftime('%Y-%m-%d %H:%M:%S')
        
        logger.info(f"Starting log pruning (dry_run={dry_run})")
        logger.info(f"Retention period: {days_to_keep} days")
        logger.info(f"Cutoff date (UTC): {cutoff_date_str}")
        logger.info(f"Will delete logs with received_timestamp < {cutoff_date_str}")
        
        with conn.cursor() as cursor:
            # First, count how many rows would be affected
            count_sql = """
                SELECT COUNT(*) as count 
                FROM fns_logs 
                WHERE received_timestamp < %s
            """
            cursor.execute(count_sql, (cutoff_date_str,))
            result = cursor.fetchone()
            rows_to_delete = result['count'] if isinstance(result, dict) else result[0]
            
            logger.info(f"Found {rows_to_delete} log entries to delete")
            
            if dry_run:
                logger.info("DRY RUN: No rows were actually deleted")
                return (0, cutoff_date)
            
            if rows_to_delete == 0:
                logger.info("No logs to prune")
                return (0, cutoff_date)
            
            # Perform the deletion
            delete_sql = """
                DELETE FROM fns_logs 
                WHERE received_timestamp < %s
            """
            cursor.execute(delete_sql, (cutoff_date_str,))
            rows_deleted = cursor.rowcount
            
            # Commit the transaction
            conn.commit()
            
            logger.info(f"Successfully deleted {rows_deleted} log entries")
            
            # Optionally, optimize the table to reclaim space
            if rows_deleted > 0:
                logger.info("Optimizing table to reclaim space...")
                try:
                    cursor.execute("OPTIMIZE TABLE fns_logs")
                    logger.info("Table optimization completed")
                except Exception as e:
                    logger.warning(f"Table optimization failed (non-critical): {e}")
            
            return (rows_deleted, cutoff_date)
            
    except Exception as e:
        logger.error(f"Error during log pruning: {e}", exc_info=True)
        if conn:
            conn.rollback()
        sys.exit(1)
    finally:
        if conn:
            conn.close()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Prune old FNS log entries from the database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run with default retention period
  python3 prune_logs.py --dry-run
  
  # Actually prune with default retention period (30 days)
  python3 prune_logs.py
  
  # Prune with custom retention period (60 days)
  python3 prune_logs.py --days 60
        """
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=None,
        help=f'Number of days to keep (default: {APP_CONFIG["days_to_keep_logs"]} from app_config)'
    )
    
    args = parser.parse_args()
    
    # Determine retention period
    days_to_keep = args.days if args.days is not None else APP_CONFIG['days_to_keep_logs']
    
    if days_to_keep < 1:
        logger.error("Retention period must be at least 1 day")
        sys.exit(1)
    
    # Perform pruning
    rows_deleted, cutoff_date = prune_logs(days_to_keep, dry_run=args.dry_run)
    
    if not args.dry_run:
        logger.info(f"Pruning completed successfully. Deleted {rows_deleted} rows.")
    else:
        logger.info("Dry run completed. No rows were deleted.")


if __name__ == '__main__':
    main()

