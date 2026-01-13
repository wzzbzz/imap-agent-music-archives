# Cron Setup Instructions

## Files Created

1. **run_workflow.sh** - Wrapper script to run individual workflows
2. **run_manifests.sh** - Wrapper script to generate manifests and track registry
3. **crontab.example** - Sample crontab entries

## Installation Steps

### 1. Copy files to your CentOS server

Copy these files to your email_archiving directory:
- run_workflow.sh
- run_manifests.sh
- crontab.example

### 2. Make scripts executable

```bash
cd /home/jackiepuppet/email_archiving
chmod +x run_workflow.sh run_manifests.sh
```

### 3. Edit crontab.example

Update the paths in `crontab.example` to match your installation directory.
The default assumes: `/home/jackiepuppet/email_archiving`

### 4. Install crontab

```bash
crontab -e
```

Then paste the contents of `crontab.example` into your crontab file.

Or use this one-liner:
```bash
crontab crontab.example
```

### 5. Verify crontab is installed

```bash
crontab -l
```

## Schedule

The default schedule runs:
- **sonic_twist**: Every hour at :05 (12:05, 1:05, 2:05, etc.)
- **even_more_cake**: Every hour at :20 (12:20, 1:20, 2:20, etc.)
- **off_the_grid**: Every hour at :35 (12:35, 1:35, 2:35, etc.)
- **Manifests/Registry**: Every hour at :50 (12:50, 1:50, 2:50, etc.)
- **Log cleanup**: Daily at 2:00 AM (removes logs older than 30 days)

## Logs

All output is logged to `logs/<workflow>.log` or `logs/manifests.log`

View logs:
```bash
# View sonic_twist logs
tail -f logs/sonic_twist.log

# View all recent activity
tail -f logs/*.log

# Check for errors
grep -i error logs/*.log
```

## Customization

### Change Schedule

Edit the crontab timing fields:
```
# Format: minute hour day month weekday command
#         0-59   0-23 1-31 1-12  0-7
```

Examples:
```bash
# Every 2 hours at :05
5 */2 * * * /path/to/run_workflow.sh sonic_twist

# Every day at 3:30 AM
30 3 * * * /path/to/run_workflow.sh sonic_twist

# Every Monday at 9:00 AM
0 9 * * 1 /path/to/run_workflow.sh sonic_twist
```

### Disable a Workflow

Comment out the line in your crontab:
```bash
# 5 * * * * /home/jackiepuppet/email_archiving/run_workflow.sh sonic_twist
```

## Troubleshooting

### Check if cron is running
```bash
systemctl status crond
```

### Check cron logs
```bash
tail -f /var/log/cron
```

### Test scripts manually
```bash
./run_workflow.sh sonic_twist
./run_manifests.sh
```

### Common issues

1. **Scripts not executing**: Make sure they're executable (`chmod +x`)
2. **Python not found**: Verify pyenv paths in wrapper scripts
3. **Permission denied**: Check file ownership and permissions
4. **No output**: Check that log directory exists and is writable
