"""
VTOP Watchdog - Automated Data Monitoring System
Monitors VTOP data and sends notifications when changes are detected
"""
import asyncio
import json
import os
import time
import hashlib
from datetime import datetime
from dotenv import load_dotenv
from authentication import AuthService, AuthError
from data_service import ProfileInfoService, AttendanceDataService, MarksDataService

# Load environment variables
load_dotenv()


class VTOPWatchdog:
    """Main watchdog class for monitoring VTOP data"""
    
    def __init__(self):
        self.last_state_file = 'last_state.json'
        self.check_interval = int(os.getenv('CHECK_INTERVAL_HOURS', '6')) * 60 * 60
        self.send_email_always = os.getenv('SEND_EMAIL_ALWAYS', 'false').lower() == 'true'
    
    def compute_hash(self, data):
        """Compute SHA256 hash of data"""
        if data is None:
            return None
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()
    
    def load_credentials(self):
        """Load credentials from environment variables"""
        username = os.getenv('VTOP_USERNAME')
        password = os.getenv('VTOP_PASSWORD')
        semester_id = os.getenv('VTOP_SEMESTER_ID')
        
        if not username or not password:
            print("Error: VTOP_USERNAME and VTOP_PASSWORD not found in .env file")
            return None
        
        credentials = {
            'username': username,
            'password': password,
            'semesterId': semester_id,
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
    
    def load_last_state(self):
        """Load last known state with hashes"""
        if not os.path.exists(self.last_state_file):
            print(f"[Watchdog] No previous state found - first run")
            return {}
        
        try:
            with open(self.last_state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
                print(f"[Watchdog] Loaded previous state from {self.last_state_file}")
                return state
        except json.JSONDecodeError:
            print(f"[Watchdog] Invalid state file - treating as first run")
            return {}
        except Exception as e:
            print(f"[Watchdog] Error loading state: {e} - treating as first run")
            return {}
    
    def save_last_state(self, state):
        """Save current state with hashes"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.last_state_file) if os.path.dirname(self.last_state_file) else '.', exist_ok=True)
            
            with open(self.last_state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            
            print(f"[Watchdog] State saved to {self.last_state_file}")
        except Exception as e:
            print(f"[Watchdog] Error saving state: {e}")
    
    def detect_profile_changes(self, old_data, new_data):
        """Detect profile changes"""
        changes = []
        
        if not old_data:
            return [{'type': 'first_run', 'category': 'profile'}]
        
        old_profile = old_data.get('profile', {})
        new_profile = new_data.get('profile', {})
        
        for key in new_profile:
            if key in old_profile and old_profile[key] != new_profile[key]:
                changes.append({
                    'type': 'profile_change',
                    'field': key,
                    'old_value': old_profile[key],
                    'new_value': new_profile[key]
                })
        
        return changes
    
    def detect_attendance_changes(self, old_data, new_data):
        """Detect attendance changes"""
        changes = []
        
        if not old_data:
            return [{'type': 'first_run', 'category': 'attendance'}]
        
        old_attendance = {item['courseCode']: item for item in old_data.get('attendance', [])}
        new_attendance = {item['courseCode']: item for item in new_data.get('attendance', [])}
        
        for code, new_item in new_attendance.items():
            if code in old_attendance:
                old_item = old_attendance[code]
                
                # Check percentage change
                if old_item['attendancePercentage'] != new_item['attendancePercentage']:
                    changes.append({
                        'type': 'attendance_change',
                        'courseCode': code,
                        'courseTitle': new_item['courseTitle'],
                        'oldPercentage': old_item['attendancePercentage'],
                        'newPercentage': new_item['attendancePercentage'],
                        'oldAttended': old_item['attendedClasses'],
                        'newAttended': new_item['attendedClasses'],
                        'oldTotal': old_item['totalClasses'],
                        'newTotal': new_item['totalClasses']
                    })
                
                # Check if new classes were added
                elif old_item['totalClasses'] != new_item['totalClasses']:
                    changes.append({
                        'type': 'new_classes',
                        'courseCode': code,
                        'courseTitle': new_item['courseTitle'],
                        'oldTotal': old_item['totalClasses'],
                        'newTotal': new_item['totalClasses'],
                        'attended': new_item['attendedClasses'],
                        'percentage': new_item['attendancePercentage']
                    })
            else:
                changes.append({
                    'type': 'new_course',
                    'courseCode': code,
                    'courseTitle': new_item['courseTitle']
                })
        
        return changes
    
    def detect_marks_changes(self, old_data, new_data):
        """Detect marks changes"""
        changes = []
        
        if not old_data:
            return [{'type': 'first_run', 'category': 'marks'}]
        
        old_courses = {course['courseCode']: course for course in old_data.get('courses', [])}
        new_courses = {course['courseCode']: course for course in new_data.get('courses', [])}
        
        for code, new_course in new_courses.items():
            if code in old_courses:
                old_course = old_courses[code]
                old_assessments = {a['markTitle']: a for a in old_course.get('assessments', [])}
                new_assessments = {a['markTitle']: a for a in new_course.get('assessments', [])}
                
                for title, new_assessment in new_assessments.items():
                    if title not in old_assessments:
                        # New assessment posted
                        changes.append({
                            'type': 'new_marks',
                            'courseCode': code,
                            'courseTitle': new_course['courseTitle'],
                            'assessment': title,
                            'scored': new_assessment['scoredMark'],
                            'max': new_assessment['maxMark'],
                            'weightage': new_assessment['weightageMark'],
                            'maxWeightage': new_assessment['weightagePercentage']
                        })
                    elif old_assessments[title]['scoredMark'] != new_assessment['scoredMark']:
                        # Marks updated
                        changes.append({
                            'type': 'marks_updated',
                            'courseCode': code,
                            'courseTitle': new_course['courseTitle'],
                            'assessment': title,
                            'oldScore': old_assessments[title]['scoredMark'],
                            'newScore': new_assessment['scoredMark'],
                            'max': new_assessment['maxMark']
                        })
            else:
                # New course with marks
                changes.append({
                    'type': 'new_course_marks',
                    'courseCode': code,
                    'courseTitle': new_course['courseTitle'],
                    'assessments': len(new_course.get('assessments', []))
                })
        
        return changes
    
    def format_email_body(self, changes, profile_data, attendance_data, marks_data):
        """Format detailed HTML email with changes and current data"""
        now = datetime.now()
        
        # HTML email with proper tables
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: Arial, sans-serif;
            font-size: 14px;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 10px;
        }}
        .header {{
            background-color: #2c3e50;
            color: white;
            padding: 15px;
            text-align: center;
            margin-bottom: 20px;
        }}
        .section {{
            margin-bottom: 25px;
        }}
        .section-title {{
            background-color: #34495e;
            color: white;
            padding: 10px;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 15px;
        }}
        th {{
            background-color: #95a5a6;
            color: white;
            padding: 10px;
            text-align: left;
            font-weight: bold;
        }}
        td {{
            padding: 8px;
            border-bottom: 1px solid #ddd;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        .change-item {{
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 10px;
            margin-bottom: 10px;
        }}
        .change-title {{
            font-weight: bold;
            color: #856404;
            margin-bottom: 5px;
        }}
        .safe {{
            color: #27ae60;
            font-weight: bold;
        }}
        .warning {{
            color: #e74c3c;
            font-weight: bold;
        }}
        .footer {{
            background-color: #ecf0f1;
            padding: 15px;
            text-align: center;
            font-size: 12px;
            color: #7f8c8d;
            margin-top: 20px;
        }}
        .info-table {{
            background-color: white;
        }}
        .info-table td:first-child {{
            font-weight: bold;
            width: 150px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h2>VTOP Update Alert</h2>
        <p>{now.strftime('%A, %B %d, %Y at %I:%M %p')}</p>
    </div>
"""
        
        # Changes section
        if changes:
            html += '<div class="section">'
            html += '<div class="section-title">CHANGES DETECTED</div>'
            
            for change in changes:
                if change['type'] == 'first_run':
                    html += f'<div class="change-item">'
                    html += f'<div class="change-title">Initial Data Extraction</div>'
                    html += f'{change["category"].upper()} data extracted for the first time'
                    html += '</div>'
                
                elif change['type'] == 'profile_change':
                    html += '<div class="change-item">'
                    html += '<div class="change-title">Profile Updated</div>'
                    html += f'<strong>Field:</strong> {change["field"]}<br>'
                    html += f'<strong>Changed:</strong> {change["old_value"]} → {change["new_value"]}'
                    html += '</div>'
                
                elif change['type'] == 'attendance_change':
                    status_class = "safe" if change['newPercentage'] >= 75 else "warning"
                    html += '<div class="change-item">'
                    html += '<div class="change-title">Attendance Updated</div>'
                    html += f'<strong>Course:</strong> {change["courseTitle"]} ({change["courseCode"]})<br>'
                    html += f'<strong>Percentage:</strong> {change["oldPercentage"]}% → <span class="{status_class}">{change["newPercentage"]}%</span><br>'
                    html += f'<strong>Classes:</strong> {change["newAttended"]}/{change["newTotal"]}<br>'
                    html += f'<strong>Change:</strong> +{change["newAttended"] - change["oldAttended"]} attended, '
                    html += f'+{change["newTotal"] - change["oldTotal"]} total'
                    html += '</div>'
                
                elif change['type'] == 'new_classes':
                    html += '<div class="change-item">'
                    html += '<div class="change-title">New Classes Added</div>'
                    html += f'<strong>Course:</strong> {change["courseTitle"]} ({change["courseCode"]})<br>'
                    html += f'<strong>Total Classes:</strong> {change["oldTotal"]} → {change["newTotal"]}<br>'
                    html += f'<strong>Current:</strong> {change["attended"]}/{change["newTotal"]} ({change["percentage"]}%)'
                    html += '</div>'
                
                elif change['type'] == 'new_marks':
                    percentage = (change['scored'] / change['max'] * 100) if change['max'] else 0
                    html += '<div class="change-item">'
                    html += '<div class="change-title">New Marks Posted</div>'
                    html += f'<strong>Course:</strong> {change["courseTitle"]} ({change["courseCode"]})<br>'
                    html += f'<strong>Assessment:</strong> {change["assessment"]}<br>'
                    html += f'<strong>Scored:</strong> {change["scored"]}/{change["max"]} ({percentage:.1f}%)<br>'
                    html += f'<strong>Weightage:</strong> {change["weightage"]}/{change["maxWeightage"]}'
                    html += '</div>'
                
                elif change['type'] == 'marks_updated':
                    html += '<div class="change-item">'
                    html += '<div class="change-title">Marks Updated</div>'
                    html += f'<strong>Course:</strong> {change["courseTitle"]} ({change["courseCode"]})<br>'
                    html += f'<strong>Assessment:</strong> {change["assessment"]}<br>'
                    html += f'<strong>Score Changed:</strong> {change["oldScore"]} → {change["newScore"]}/{change["max"]}'
                    html += '</div>'
            
            html += '</div>'
        
        # Profile section
        if profile_data:
            profile = profile_data.get('profile', {})
            html += '<div class="section">'
            html += '<div class="section-title">PROFILE</div>'
            html += '<table class="info-table">'
            html += f'<tr><td>Name</td><td>{profile.get("name", "N/A")}</td></tr>'
            html += f'<tr><td>Register No</td><td>{profile.get("registerNumber", "N/A")}</td></tr>'
            html += f'<tr><td>Email</td><td>{profile.get("vitEmail", "N/A")}</td></tr>'
            html += f'<tr><td>Program</td><td>{profile.get("program", "N/A")}</td></tr>'
            html += f'<tr><td>School</td><td>{profile.get("schoolName", "N/A")}</td></tr>'
            if profile.get('hostelBlock'):
                html += f'<tr><td>Hostel</td><td>{profile.get("hostelBlock", "N/A")}, Room {profile.get("roomNumber", "N/A")}</td></tr>'
            html += '</table></div>'
        
        # Attendance section
        if attendance_data:
            attendance_list = attendance_data.get('attendance', [])
            metadata = attendance_data.get('metadata', {})
            
            html += '<div class="section">'
            html += '<div class="section-title">ATTENDANCE SUMMARY</div>'
            html += '<table class="info-table">'
            html += f'<tr><td>Total Subjects</td><td>{metadata.get("totalSubjects", 0)}</td></tr>'
            html += f'<tr><td>Overall Attendance</td><td><strong>{metadata.get("overallPercentage", 0)}%</strong></td></tr>'
            html += f'<tr><td>Total Classes</td><td>{metadata.get("totalAttendedClasses", 0)}/{metadata.get("totalClasses", 0)}</td></tr>'
            html += '</table>'
            
            html += '<table>'
            html += '<tr><th>Course</th><th>Attended</th><th>Percentage</th></tr>'
            
            for item in sorted(attendance_list, key=lambda x: x['attendancePercentage']):
                status_class = "safe" if item['attendancePercentage'] >= 75 else "warning"
                html += f'<tr>'
                html += f'<td>{item["courseTitle"]}</td>'
                html += f'<td>{item["attendedClasses"]}/{item["totalClasses"]}</td>'
                html += f'<td class="{status_class}">{item["attendancePercentage"]}%</td>'
                html += '</tr>'
            
            html += '</table></div>'
        
        # Marks section
        if marks_data:
            courses = marks_data.get('courses', [])
            metadata = marks_data.get('metadata', {})
            
            html += '<div class="section">'
            html += '<div class="section-title">MARKS SUMMARY</div>'
            html += '<table class="info-table">'
            html += f'<tr><td>Total Courses</td><td>{metadata.get("totalCourses", 0)}</td></tr>'
            html += f'<tr><td>Total Assessments</td><td>{metadata.get("totalAssessments", 0)}</td></tr>'
            html += '</table>'
            
            for course in courses:
                html += f'<h4>{course["courseTitle"]} ({course["courseCode"]})</h4>'
                html += f'<p><strong>Faculty:</strong> {course["faculty"]} | <strong>Slot:</strong> {course["slot"]}</p>'
                
                assessments = course.get('assessments', [])
                if assessments:
                    html += '<table>'
                    html += '<tr><th>Assessment</th><th>Scored</th><th>Weightage</th></tr>'
                    
                    for assessment in assessments:
                        html += '<tr>'
                        html += f'<td>{assessment["markTitle"]}</td>'
                        html += f'<td>{assessment["scoredMark"]}/{assessment["maxMark"]}</td>'
                        html += f'<td>{assessment["weightageMark"]}/{assessment["weightagePercentage"]}</td>'
                        html += '</tr>'
                    
                    html += '</table>'
            
            html += '</div>'
        
        # Footer
        next_check = datetime.fromtimestamp(time.time() + self.check_interval)
        html += '<div class="footer">'
        html += '<p>This is an automated notification from WatchPup - VTOP Data Watchdog</p>'
        html += f'<p>Next check scheduled at: {next_check.strftime("%I:%M %p on %B %d, %Y")}</p>'
        html += '</div>'
        
        html += '</body></html>'
        
        return html
    
    def send_email(self, subject, html_body, config):
        """Send HTML email via Gmail SMTP"""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        msg = MIMEMultipart('alternative')
        msg['From'] = config['email']
        msg['To'] = config['to_email']
        msg['Subject'] = subject
        
        # Attach HTML version
        html_part = MIMEText(html_body, 'html')
        msg.attach(html_part)
        
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(config['email'], config['app_password'])
            server.send_message(msg)
    
    def send_notifications(self, changes, profile_data, attendance_data, marks_data, credentials):
        """Send notifications via configured methods"""
        # Check if we should send email
        should_send = False
        
        if self.send_email_always:
            should_send = True
            print("[Notification] SEND_EMAIL_ALWAYS is enabled - sending email")
        elif changes:
            should_send = True
            print(f"[Notification] {len(changes)} change(s) detected - sending email")
        else:
            print("[Notification] No changes detected and SEND_EMAIL_ALWAYS is disabled - skipping email")
            return
        
        if not should_send:
            return
        
        now = datetime.now()
        subject = f"VTOP Update - {now.strftime('%I:%M %p, %b %d, %Y')}"
        html_body = self.format_email_body(changes, profile_data, attendance_data, marks_data)
        
        notifications = credentials.get('notifications', {})
        
        # Gmail notification
        if notifications.get('gmail', {}).get('enabled'):
            try:
                self.send_email(subject, html_body, notifications['gmail'])
                print("[Notification] Email sent successfully")
            except Exception as e:
                print(f"[Notification] Email failed: {e}")
        
        # WhatsApp notification (summary only)
        if notifications.get('whatsapp', {}).get('enabled'):
            try:
                from twilio.rest import Client
                summary = f"VTOP Update - {now.strftime('%I:%M %p')}\n\n"
                if changes:
                    summary += f"{len(changes)} change(s) detected\n"
                else:
                    summary += "No changes - routine check\n"
                summary += "Check your email for details."
                
                client = Client(notifications['whatsapp']['account_sid'], notifications['whatsapp']['auth_token'])
                client.messages.create(
                    from_=notifications['whatsapp']['from_number'],
                    body=summary,
                    to=notifications['whatsapp']['to_number']
                )
                print("[Notification] WhatsApp sent successfully")
            except Exception as e:
                print(f"[Notification] WhatsApp failed: {e}")
    
    async def check_updates(self):
        """Check for updates and send notifications"""
        print(f"\n{'='*70}")
        print(f"VTOP Watchdog - Checking for updates")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}\n")
        
        credentials = self.load_credentials()
        if not credentials:
            return
        
        username = credentials.get('username')
        password = credentials.get('password')
        semester_id = credentials.get('semesterId')
        
        # Authenticate
        auth_service = AuthService()
        try:
            await auth_service.initialize('authentication/captcha/vellore_weights.json')
            success, error_code, message = await auth_service.login(username, password, max_attempts=3)
            
            if not success:
                print(f"[Watchdog] Authentication failed: {message}")
                return
            
            print("[Watchdog] Authentication successful\n")
            
            # Load last state
            last_state = self.load_last_state()
            all_changes = []
            
            # Extract profile
            print("[Watchdog] Extracting profile...")
            profile_service = ProfileInfoService(auth_service.session)
            profile_data = None
            if profile_service.run():
                profile_data = profile_service.get_saved_profile()
                new_hash = self.compute_hash(profile_data)
                old_hash = last_state.get('profile_hash')
                
                if new_hash != old_hash:
                    changes = self.detect_profile_changes(last_state.get('profile_data'), profile_data)
                    all_changes.extend(changes)
                    last_state['profile_hash'] = new_hash
                    last_state['profile_data'] = profile_data
                    print(f"   Changes detected: {len(changes)}")
                else:
                    print(f"   No changes")
            
            # Extract attendance
            attendance_data = None
            if semester_id:
                print("[Watchdog] Extracting attendance...")
                attendance_service = AttendanceDataService(auth_service.session)
                if attendance_service.run(semester_id):
                    attendance_data = attendance_service.get_saved_attendance()
                    new_hash = self.compute_hash(attendance_data)
                    old_hash = last_state.get('attendance_hash')
                    
                    if new_hash != old_hash:
                        changes = self.detect_attendance_changes(last_state.get('attendance_data'), attendance_data)
                        all_changes.extend(changes)
                        last_state['attendance_hash'] = new_hash
                        last_state['attendance_data'] = attendance_data
                        print(f"   Changes detected: {len(changes)}")
                    else:
                        print(f"   No changes")
            
            # Extract marks
            marks_data = None
            if semester_id:
                print("[Watchdog] Extracting marks...")
                marks_service = MarksDataService(auth_service.session)
                if marks_service.run(semester_id):
                    marks_data = marks_service.get_saved_marks()
                    new_hash = self.compute_hash(marks_data)
                    old_hash = last_state.get('marks_hash')
                    
                    if new_hash != old_hash:
                        changes = self.detect_marks_changes(last_state.get('marks_data'), marks_data)
                        all_changes.extend(changes)
                        last_state['marks_hash'] = new_hash
                        last_state['marks_data'] = marks_data
                        print(f"   Changes detected: {len(changes)}")
                    else:
                        print(f"   No changes")
            
            # Save state
            last_state['last_check'] = datetime.now().isoformat()
            self.save_last_state(last_state)
            
            # Send notifications
            if all_changes:
                print(f"\n[Watchdog] Total changes: {len(all_changes)}")
                print("[Watchdog] Sending notifications...")
                self.send_notifications(all_changes, profile_data, attendance_data, marks_data, credentials)
            else:
                print("\n[Watchdog] No changes detected")
            
        except Exception as e:
            print(f"[Watchdog] Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            auth_service.logout()
    
    async def run(self):
        """Run watchdog continuously"""
        print("\n" + "="*70)
        print(" "*20 + "VTOP WATCHDOG STARTED")
        print("="*70)
        print(f"\nMonitoring interval: {self.check_interval / 3600} hours")
        print("Press Ctrl+C to stop\n")
        
        while True:
            try:
                await self.check_updates()
                next_check = datetime.fromtimestamp(time.time() + self.check_interval)
                print(f"\n[Watchdog] Next check at: {next_check.strftime('%I:%M %p on %B %d, %Y')}\n")
                await asyncio.sleep(self.check_interval)
            except KeyboardInterrupt:
                print("\n\n[Watchdog] Stopped by user")
                break
            except Exception as e:
                print(f"\n[Watchdog] Error in main loop: {e}")
                print("[Watchdog] Retrying in 5 minutes...")
                await asyncio.sleep(300)
    
    async def run_once(self):
        """Run watchdog once (for GitHub Actions)"""
        print("\n" + "="*70)
        print(" "*20 + "VTOP WATCHDOG - SINGLE CHECK")
        print("="*70 + "\n")
        
        await self.check_updates()
        
        print("\n" + "="*70)
        print("SINGLE CHECK COMPLETE")
        print("="*70 + "\n")


if __name__ == "__main__":
    import sys
    import io
    
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    watchdog = VTOPWatchdog()
    
    # Check if running in single-check mode (for GitHub Actions)
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        asyncio.run(watchdog.run_once())
    else:
        asyncio.run(watchdog.run())
