# Notification Setup Guide

Configure WatchPup to send you alerts when your VTOP data changes.

## Notification Methods

### 1. WhatsApp (via Twilio)

**Pros:** Instant delivery, widely used, rich formatting
**Cons:** Requires Twilio account, costs money after free trial
**Limitations:** 1 message per second, requires verified numbers

**Setup:**
1. Create account at [twilio.com](https://www.twilio.com)
2. Get WhatsApp sandbox number or buy a Twilio number
3. Add to `.env` file:
```env
WHATSAPP_ENABLED=true
WHATSAPP_ACCOUNT_SID=your_twilio_account_sid
WHATSAPP_AUTH_TOKEN=your_twilio_auth_token
WHATSAPP_FROM_NUMBER=whatsapp:+14155238886
WHATSAPP_TO_NUMBER=whatsapp:+919876543210
```

**Cost:** Free trial ($15 credit), then ~$0.005 per message

---

### 2. Gmail (via SMTP)

**Pros:** Free, reliable, no rate limits
**Cons:** Requires app password, may go to spam
**Limitations:** 500 emails per day

**Setup:**
1. Enable 2-factor authentication on your Gmail
2. Generate app password: [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Add to `.env` file:
```env
GMAIL_ENABLED=true
GMAIL_EMAIL=your.email@gmail.com
GMAIL_APP_PASSWORD=your_16_char_app_password
GMAIL_TO_EMAIL=recipient@example.com
```

**Cost:** Free

---

### 3. SMS (via Twilio)

**Pros:** Works on any phone, no internet required
**Cons:** Costs money, character limit
**Limitations:** 160 characters per message, 1 message per second

**Setup:**
1. Create account at [twilio.com](https://www.twilio.com)
2. Buy a phone number (~$1/month)
3. Add to `.env` file:
```env
SMS_ENABLED=true
SMS_ACCOUNT_SID=your_twilio_account_sid
SMS_AUTH_TOKEN=your_twilio_auth_token
SMS_FROM_NUMBER=+12345678900
SMS_TO_NUMBER=+919876543210
```

**Cost:** ~$1/month for number + $0.0075 per SMS

---

## Complete Configuration Example

Create a `.env` file in the project root:

```env
# VTOP Credentials
VTOP_USERNAME=23BAI1214
VTOP_PASSWORD=your_password
VTOP_SEMESTER_ID=CH20252605

# Gmail Notifications
GMAIL_ENABLED=true
GMAIL_EMAIL=your.email@gmail.com
GMAIL_APP_PASSWORD=abcdefghijklmnop
GMAIL_TO_EMAIL=your.email@gmail.com

# WhatsApp Notifications
WHATSAPP_ENABLED=true
WHATSAPP_ACCOUNT_SID=ACxxxxxxxxxxxxx
WHATSAPP_AUTH_TOKEN=your_auth_token
WHATSAPP_FROM_NUMBER=whatsapp:+14155238886
WHATSAPP_TO_NUMBER=whatsapp:+919876543210

# SMS Notifications (disabled)
SMS_ENABLED=false

# Watchdog Settings
CHECK_INTERVAL_HOURS=6
```

## Notification Content

WatchPup sends alerts for:

### Marks Updates
```
🎓 New Marks Posted!

Course: Compiler Design (BCSE307L)
Assessment: CAT-1
Scored: 30/50 (60%)
Weightage: 9/15

View details: data/marks-data.json
```

### Attendance Updates
```
📅 Attendance Updated!

Course: Deep Learning (BCSE332L)
Attended: 18/22 classes
Percentage: 82% (was 80%)

Status: Safe ✅
```

### Profile Changes
```
👤 Profile Updated!

Changed fields:
- Room Number: 924 → 925
- Mess: Food Park → New Mess

Updated: 2026-02-12 10:30 AM
```

## Testing Notifications

Run the test script to verify your setup:
```bash
python test_notifications.py
```

This sends a test message to all enabled notification methods.

## Troubleshooting

### WhatsApp not working
- Verify your Twilio sandbox is active
- Check if recipient number is verified in sandbox
- Ensure number format includes country code

### Gmail not working
- Verify app password is correct (16 characters, no spaces)
- Check if "Less secure app access" is enabled
- Look in spam folder

### SMS not working
- Verify Twilio account has sufficient balance
- Check if phone number is verified
- Ensure number format includes country code (+91...)

## Rate Limits & Best Practices

- **WhatsApp:** Max 1 message/second, 100 messages/hour
- **Gmail:** Max 500 emails/day
- **SMS:** Max 1 message/second, costs apply

**Recommendations:**
- Use Gmail for detailed reports (free, unlimited)
- Use WhatsApp for urgent alerts (instant, but costs)
- Avoid SMS unless necessary (expensive)
- Set check interval to 6+ hours to avoid spam

## Privacy & Security

- Store credentials securely (never commit to git)
- Use app passwords instead of main passwords
- Rotate credentials periodically
- Monitor notification service usage/costs
- Review Twilio/Gmail security settings regularly

## Alternative Methods

### Telegram Bot (Free)
- Create bot via [@BotFather](https://t.me/botfather)
- Get bot token and chat ID
- Free, unlimited messages
- Requires Python `python-telegram-bot` package

### Discord Webhook (Free)
- Create webhook in Discord server settings
- Send JSON POST requests
- Free, unlimited messages
- Good for group notifications

### Pushbullet (Free tier available)
- Push notifications to phone/browser
- Free tier: 500 pushes/month
- Easy setup, cross-platform

## Support

For issues or questions:
1. Check debug logs in `debug/` folder
2. Verify credentials in `credentials.json`
3. Test notification services independently
4. Review service provider documentation



Method	Cost	Pros	Cons
Gmail	Free	Unlimited, reliable	May go to spam
WhatsApp	~$0.005/msg	Instant, popular	Requires Twilio account
SMS	~$0.0075/msg	Works anywhere	Character limit, costs