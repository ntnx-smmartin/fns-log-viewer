# fns-log-viewer
A simple python flask app for displaying Flow Network Security logs that have been collected via syslog and stored in a MySQL/MariaDB database. Created with the assistance of AI tools.

## Requirements
This assumes that Flow Network Security is set up to send syslogs to a syslog server that is storing the logs in a MySQL-style database that is reachable from where the app is running. This can be local or remote.

## Configuration

### Environment Variables

The application uses environment variables for configuration, particularly for sensitive database credentials. **Never commit credentials to version control.**

1. Copy the example environment file:
   ```bash
   cp env.example .env
   ```

2. Edit `.env` with your actual database credentials:
   ```bash
   # Database Configuration
   FNS_DB_HOST=127.0.0.1
   FNS_DB_USER=rsyslog
   FNS_DB_PASSWORD=your_actual_password_here
   FNS_DB_NAME=Syslog
   
   # Application Configuration
   FNS_DAYS_TO_KEEP_LOGS=30
   FNS_DEFAULT_TIMEZONE=UTC
   ```

3. Load environment variables before running the application:
   ```bash
   # Option 1: Export manually
   export FNS_DB_PASSWORD="your_password"
   export FNS_DB_HOST="127.0.0.1"
   # ... etc
   
   # Option 2: Use a tool like python-dotenv (recommended)
   # Install: pip install python-dotenv
   # Then create a .env file and the app will load it automatically
   ```

   **Note:** If using `python-dotenv`, you'll need to add it to `requirements.txt` and load it in `app.py`. Alternatively, you can source the `.env` file manually:
   ```bash
   set -a
   source .env
   set +a
   python3 app.py
   ```

### Security Note

The `.env` file is excluded from version control via `.gitignore`. **Never commit files containing passwords or other sensitive information.**

**Important:** The `conf/fns-rsyslog.conf` file also contains database credentials. This is a template file for rsyslog configuration. When deploying, ensure you:
1. Update the password in your actual rsyslog configuration file
2. Do not commit the actual rsyslog configuration with real credentials to version control
3. Store rsyslog configuration files securely on the server

## Parsing the logs.

A sample Flow Network Security log looks like this:

`2025-12-11T12:51:08.857757+00:00 ahv-host-1 ahv INFO:2025/12/11 12:51:05  [c06984c8-d504-4322-bd52-fff217781885] Default Global Policy [Destroy] SRC=100.64.128.20 DST=34.243.160.129 PROTO=TCP SPORT=48256 DPORT=443 ACTION=ALLOW DIRECTION=OUTBOUND ORIG: PKTS=10 BYTES=1314 REPLY: PKTS=10 BYTES=4429 DESCRIPTION=Allow Outbound Internet via HTTP and HTTPS`

The following fields need to be extracted, shown with their values from the sample log above:
 - **received_timestamp** - 2025-12-11T12:51:08.857757+00:00
 - **hostname** - ahv-host-1
 - **os** - ahv
 - **event_timestamp** - 2025/12/11 12:51:05
 - **rule_uuid** - c06984c8-d504-4322-bd52-fff217781885
 - **rule_name** - Default Global Policy
 - **event_type** - Destroy
 - **source** - 100.64.128.20 
 - **destination** - 34.243.160.129
 - **protocol** - TCP
 - **source_port** - 48256
 - **destination_port** - 443
 - **action** - ALLOW
 - **direction** - OUTBOUND
 - **originator_packets** - 10
 - **originator_bytes** - 1314
 - **reply_packets** - 10
 - **reply_bytes** 4429
 - **description** *(not always present)* - Allow Outbound Internet via HTTP and HTTPS

I use rsyslog 8.2312.0 to capture and parse the logs and store them in a MariaDB instance, and an example rsyslog conf file is included in the conf directory.

### Creating the Table to store the logs.
To create the table, use the following:

CREATE TABLE fns_logs (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    received_timestamp DATETIME(6) NOT NULL,
    hostname VARCHAR(255) NOT NULL,
    os VARCHAR(50) NOT NULL,
    event_timestamp DATETIME NOT NULL,
    rule_uuid CHAR(36) NOT NULL,
    rule_name VARCHAR(255) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    source VARCHAR(45) NOT NULL,
    destination VARCHAR(45) NOT NULL,
    protocol VARCHAR(10) NOT NULL,
    source_port INT UNSIGNED NOT NULL,
    destination_port INT UNSIGNED NOT NULL,
    action VARCHAR(20) NOT NULL,
    direction VARCHAR(20) NOT NULL,
    originator_packets BIGINT UNSIGNED NOT NULL,
    originator_bytes BIGINT UNSIGNED NOT NULL,
    reply_packets BIGINT UNSIGNED NOT NULL,
    reply_bytes BIGINT UNSIGNED NOT NULL,
    description TEXT NULL,
    INDEX idx_received_timestamp (received_timestamp),
    INDEX idx_hostname (hostname),
    INDEX idx_event_timestamp (event_timestamp),
    INDEX idx_rule_uuid (rule_uuid),
    INDEX idx_source (source),
    INDEX idx_destination (destination),
    INDEX idx_action (action)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

## Running the app
The app runs as a basic Flask app, and can be launched to run in the background with 
`nohup python3 app.py > /var/log/fnslogviewer.log 2>&1 &`

It is recommended that this be placed behind a load balancer or reverse proxy of some sort.

## Log Pruning

To prevent the database from growing indefinitely, the application includes an automated log pruning system. The retention period is configured in `app_config.py` (default: 30 days).

### Manual Pruning

You can manually run the pruning script:

```bash
# Dry run to see what would be deleted
python3 prune_logs.py --dry-run

# Actually prune logs (uses retention period from app_config.py)
python3 prune_logs.py

# Prune with custom retention period
python3 prune_logs.py --days 60
```

### Automated Pruning (Recommended)

Set up a cron job to run the pruning script automatically:

**Option 1: Use the setup script (easiest)**
```bash
chmod +x setup_cron.sh
./setup_cron.sh
```

**Option 2: Manual cron setup**
```bash
# Edit crontab
crontab -e

# Add this line to run daily at 2:00 AM (adjust path as needed)
0 2 * * * /path/to/fns-log-viewer/bin/python3 /path/to/fns-log-viewer/prune_logs.py >> /var/log/fns-log-pruner-cron.log 2>&1
```

**Option 3: Systemd Timer (Linux)**

Create `/etc/systemd/system/fns-log-prune.service`:
```ini
[Unit]
Description=FNS Log Pruning Service
After=network.target mysql.service

[Service]
Type=oneshot
User=your-user
WorkingDirectory=/path/to/fns-log-viewer
ExecStart=/path/to/fns-log-viewer/bin/python3 /path/to/fns-log-viewer/prune_logs.py
```

Create `/etc/systemd/system/fns-log-prune.timer`:
```ini
[Unit]
Description=Run FNS Log Pruning Daily
Requires=fns-log-prune.service

[Timer]
OnCalendar=daily
OnCalendar=02:00
Persistent=true

[Install]
WantedBy=timers.target
```

Then enable and start:
```bash
sudo systemctl enable fns-log-prune.timer
sudo systemctl start fns-log-prune.timer
```

### Pruning Behavior

- Logs are pruned based on `received_timestamp` (when the log was received by syslog)
- The script uses parameterized queries to prevent SQL injection
- After deletion, the table is optimized to reclaim disk space
- All operations are logged to `/var/log/fns-log-pruner.log`
- The script is idempotent and safe to run multiple times

