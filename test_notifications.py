"""
Test Notification Setup
Sends test messages to verify your notification configuration
"""
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def load_credentials():
    """Load credentials from environment variables"""
    username = os.getenv('VTOP_USERNAME')
    password = os.getenv('VTOP_PASSWORD')
    
    if not username or not password:
        print("Error: VTOP credentials not found in .env file")
        return None
    
    credentials = {
        'username': username,
        'password': password,
        'notifications': {}
    }
    
    # Load Gmail config
    if os.getenv('GMAIL_ENABLED', 'false').lower() == 'true':
        credentials['notifications']['gmail'] = {
            'enabled': True,
            'email': os.getenv('GMAIL_EMAIL'),
            'app_password': os.getenv('GMAIL_APP_PASSWORD'),
            'to_email': os.getenv('GMAIL_TO_EMAIL')
        }
    
    # Load WhatsApp config
    if os.getenv('WHATSAPP_ENABLED', 'false').lower() == 'true':
        credentials['notifications']['whatsapp'] = {
            'enabled': True,
            'account_sid': os.getenv('WHATSAPP_ACCOUNT_SID'),
            'auth_token': os.getenv('WHATSAPP_AUTH_TOKEN'),
            'from_number': os.getenv('WHATSAPP_FROM_NUMBER'),
            'to_number': os.getenv('WHATSAPP_TO_NUMBER')
        }
    
    # Load SMS config
    if os.getenv('SMS_ENABLED', 'false').lower() == 'true':
        credentials['notifications']['sms'] = {
            'enabled': True,
            'account_sid': os.getenv('SMS_ACCOUNT_SID'),
            'auth_token': os.getenv('SMS_AUTH_TOKEN'),
            'from_number': os.getenv('SMS_FROM_NUMBER'),
            'to_number': os.getenv('SMS_TO_NUMBER')
        }
    
    return credentials


def test_gmail(config):
    """Test Gmail notification"""
    print("\n[Testing Gmail]")
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        msg = MIMEMultipart()
        msg['From'] = config['email']
        msg['To'] = config['to_email']
        msg['Subject'] = 'WatchPup Test Notification'
        
        body = f"""
This is a test notification from WatchPup.

If you received this email, your Gmail notification setup is working correctly!

Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---
WatchPup - VTOP Data Watchdog
"""
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(config['email'], config['app_password'])
            server.send_message(msg)
        
        print("✅ Gmail test successful!")
        print(f"   Email sent to: {config['to_email']}")
        return True
    except Exception as e:
        print(f"❌ Gmail test failed: {e}")
        return False


def test_whatsapp(config):
    """Test WhatsApp notification"""
    print("\n[Testing WhatsApp]")
    try:
        from twilio.rest import Client
        
        message = f"""
🔔 WatchPup Test Notification

This is a test message from WatchPup.

If you received this WhatsApp message, your notification setup is working correctly!

Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        client = Client(config['account_sid'], config['auth_token'])
        result = client.messages.create(
            from_=config['from_number'],
            body=message,
            to=config['to_number']
        )
        
        print("✅ WhatsApp test successful!")
        print(f"   Message SID: {result.sid}")
        print(f"   Sent to: {config['to_number']}")
        return True
    except Exception as e:
        print(f"❌ WhatsApp test failed: {e}")
        return False


def test_sms(config):
    """Test SMS notification"""
    print("\n[Testing SMS]")
    try:
        from twilio.rest import Client
        
        message = f"WatchPup Test: Your SMS notification is working! Time: {datetime.now().strftime('%H:%M:%S')}"
        
        client = Client(config['account_sid'], config['auth_token'])
        result = client.messages.create(
            from_=config['from_number'],
            body=message,
            to=config['to_number']
        )
        
        print("✅ SMS test successful!")
        print(f"   Message SID: {result.sid}")
        print(f"   Sent to: {config['to_number']}")
        return True
    except Exception as e:
        print(f"❌ SMS test failed: {e}")
        return False


def main():
    print("\n" + "="*70)
    print(" "*20 + "NOTIFICATION TEST SUITE")
    print("="*70)
    
    credentials = load_credentials()
    if not credentials:
        return
    
    notifications = credentials.get('notifications', {})
    if not notifications:
        print("\nNo notification configuration found in .env file")
        print("Please set notification variables in .env. See NOTIFICATIONS.md for details.")
        return
    
    results = {}
    
    # Test Gmail
    if notifications.get('gmail', {}).get('enabled'):
        results['gmail'] = test_gmail(notifications['gmail'])
    else:
        print("\n[Gmail] Skipped (not enabled)")
    
    # Test WhatsApp
    if notifications.get('whatsapp', {}).get('enabled'):
        results['whatsapp'] = test_whatsapp(notifications['whatsapp'])
    else:
        print("\n[WhatsApp] Skipped (not enabled)")
    
    # Test SMS
    if notifications.get('sms', {}).get('enabled'):
        results['sms'] = test_sms(notifications['sms'])
    else:
        print("\n[SMS] Skipped (not enabled)")
    
    # Summary
    print("\n" + "="*70)
    print(" "*25 + "TEST SUMMARY")
    print("="*70)
    
    if not results:
        print("\nNo notification methods enabled.")
        print("Enable at least one method in .env file")
    else:
        for method, success in results.items():
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"{method.upper():15} {status}")
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    main()
