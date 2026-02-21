# WatchPup - VTOP Data Watchdog

**Automated monitoring system for VIT VTOP portal that tracks student data changes and sends notifications.**

## What It Does

WatchPup automatically monitors your VTOP data and alerts you when something changes:
- Marks updates (new assessments, grade changes)
- Attendance changes (new classes, percentage updates)
- Profile information updates
- Notifications via WhatsApp, Gmail, or SMS

## Deployment Options

### Option 1: GitHub Actions (Recommended - Free Cloud Hosting)
Run automatically in the cloud without keeping your computer on. See [DEPLOYMENT.md](DEPLOYMENT.md) for complete setup guide.

**Benefits:**
- Completely free (2,000 minutes/month)
- Runs every 6 hours automatically
- No server maintenance
- Secure credential storage

### Option 2: Local Machine
Run on your own computer with automatic startup.

**Windows:**
```cmd
setup_autostart.bat    # Setup automatic startup
start_watchdog.bat     # Start manually
stop_watchdog.bat      # Stop watchdog
```

## Quick Start (Local)

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure credentials in `.env` file:
```env
VTOP_USERNAME=your_vtop_username
VTOP_PASSWORD=your_vtop_password
VTOP_SEMESTER_ID=CH20252605
```

Copy `.env.example` to `.env` and fill in your details.

3. Run the watchdog:
```bash
python watchdog.py
```

## Features

- ✅ Automatic VTOP login with captcha solving (98%+ accuracy)
- ✅ Extracts profile, attendance, and marks data
- ✅ Detects changes by comparing with previous data
- ✅ Sends notifications when changes are detected
- ✅ Runs on schedule (configurable interval)
- ✅ Saves complete data history with timestamps

## Project Structure

```
watchpup/
├── authentication/      # VTOP login & captcha solving
├── data_service/        # Data extraction services
├── utils/              # Notification handlers
├── data/               # Extracted data (JSON)
├── debug/              # Debug logs
├── .env                # Configuration (create from .env.example)
├── .env.example        # Example configuration
├── watchdog.py         # Main watchdog script
├── main.py             # Manual data extraction
└── test_notifications.py  # Test notification setup
```

## Data Extracted

### Profile Information
- Name, register number, email
- Program, branch, school
- Hostel details, mess information

### Attendance Data
- Course-wise attendance records
- Attended/total classes, percentage
- Faculty information, registration dates

### Marks Data
- Course details (code, title, faculty, slot)
- Assessment-wise marks
- Scored marks, weightage, class average

## Notification Setup

See [NOTIFICATIONS.md](NOTIFICATIONS.md) for detailed setup instructions for:
- WhatsApp notifications (via Twilio)
- Gmail notifications (via SMTP)
- SMS notifications (via Twilio)

## Usage

### Manual Extraction
```bash
python main.py
```

### Automated Watchdog
```bash
python watchdog.py
```

The watchdog runs continuously, checking for updates every 6 hours (configurable).

## Configuration

Edit `watchdog.py` to customize:
- Check interval (default: 6 hours)
- Notification methods (WhatsApp, Gmail, SMS)
- Data comparison sensitivity

## Security Notes

- Never commit `.env` file to version control
- `data/` folder contains personal information (excluded from git)
- SSL verification disabled for VTOP's certificate issues
- Session cookies cleared after each run
- Use `.env.example` as a template for your `.env` file

## Requirements

- Python 3.7+
- Internet connection
- Valid VTOP credentials
- Notification service credentials (optional)

## License

MIT License - See LICENSE file for details
