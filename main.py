"""
VTOP Authentication System - Main Entry Point
"""
import asyncio
import sys
import os
from dotenv import load_dotenv
from authentication import AuthService, AuthError
from data_service import ProfileInfoService, AttendanceDataService, MarksDataService

# Load environment variables
load_dotenv()


async def main():
    """Main authentication flow"""
    
    print("\n" + "="*70)
    print(" "*15 + "VTOP AUTHENTICATION SYSTEM")
    print(" "*10 + "Python Implementation - VITverse App")
    print("="*70 + "\n")
    
    if len(sys.argv) >= 3:
        username = sys.argv[1]
        password = sys.argv[2]
        semester_id = sys.argv[3] if len(sys.argv) >= 4 else None
    else:
        # Load from environment variables
        username = os.getenv('VTOP_USERNAME', '').strip()
        password = os.getenv('VTOP_PASSWORD', '').strip()
        semester_id = os.getenv('VTOP_SEMESTER_ID', '').strip()
        
        if username and password:
            print(f"Loaded credentials from .env file")
            print(f"Username: {username}")
            if semester_id:
                print(f"Semester ID: {semester_id}")
        else:
            print("No credentials found in .env file")
            print("\nEnter your VTOP credentials:\n")
            username = input("Username: ").strip()
            password = input("Password: ").strip()
            if not semester_id:
                semester_id = input("Semester ID (optional): ").strip()
            print()
    
    if not username or not password:
        print("Error: Username and password are required")
        print("\nUsage:")
        print("  python main.py <username> <password>")
        print("  or run: python main.py (for interactive mode)")
        sys.exit(1)
    
    auth_service = AuthService()
    
    try:
        print("Initializing captcha recognition model...")
        
        # Check if weights file exists
        weights_path = 'authentication/captcha/vellore_weights.json'
        if not os.path.exists(weights_path):
            print(f"\nError: Model weights file not found: {weights_path}")
            print("Please ensure the file exists in the correct location")
            sys.exit(1)
        
        await auth_service.initialize(weights_path)
        
        print("\nStarting authentication process...\n")
        
        success, error_code, message = await auth_service.login(
            username=username,
            password=password,
            max_attempts=3
        )
        
        print("\n" + "="*70)
        if success:
            print("AUTHENTICATION SUCCESSFUL!")
            print("="*70)
            
            session_info = auth_service.get_session_info()
            if session_info:
                print("\nSession Information:")
                print(f"   Username: {session_info['username']}")
                print(f"   Login Time: {session_info['loginTime']}")
            
            print("\nYou are now logged into VTOP!")
            print("   The session is ready for data synchronization.")
            
            # Automatically extract profile information
            print("\n" + "="*70)
            print("EXTRACTING DATA FROM VTOP")
            print("="*70)
            
            extraction_errors = []
            
            # Step 1: Profile Information
            print("\n[Step 1/3] Extracting profile information...")
            try:
                profile_service = ProfileInfoService(auth_service.session)
                if profile_service.run():
                    saved_data = profile_service.get_saved_profile()
                    if saved_data:
                        profile = saved_data.get('profile', {})
                        print(f"   Status: Done")
                        if profile.get('name'):
                            print(f"   Name: {profile['name']}")
                else:
                    print("   Status: Error - Profile extraction failed")
                    extraction_errors.append("Profile extraction failed")
            except Exception as e:
                print(f"   Status: Error - {str(e)}")
                extraction_errors.append(f"Profile: {str(e)}")
            
            # Step 2: Attendance Data
            if semester_id:
                print(f"\n[Step 2/3] Extracting attendance data...")
                try:
                    attendance_service = AttendanceDataService(auth_service.session)
                    if attendance_service.run(semester_id):
                        saved_data = attendance_service.get_saved_attendance()
                        if saved_data:
                            metadata = saved_data.get('metadata', {})
                            print(f"   Status: Done")
                            print(f"   Total subjects: {metadata.get('totalSubjects', 0)}")
                            print(f"   Overall attendance: {metadata.get('overallPercentage', 0)}%")
                    else:
                        print("   Status: Error - Attendance extraction failed")
                        extraction_errors.append("Attendance extraction failed")
                except Exception as e:
                    print(f"   Status: Error - {str(e)}")
                    extraction_errors.append(f"Attendance: {str(e)}")
            else:
                print(f"\n[Step 2/3] Skipped - No semester ID provided")
            
            # Step 3: Marks Data
            if semester_id:
                print(f"\n[Step 3/3] Extracting marks data...")
                try:
                    marks_service = MarksDataService(auth_service.session)
                    if marks_service.run(semester_id):
                        saved_data = marks_service.get_saved_marks()
                        if saved_data:
                            metadata = saved_data.get('metadata', {})
                            print(f"   Status: Done")
                            print(f"   Total courses: {metadata.get('totalCourses', 0)}")
                            print(f"   Total assessments: {metadata.get('totalAssessments', 0)}")
                    else:
                        print("   Status: Error - Marks extraction failed")
                        extraction_errors.append("Marks extraction failed")
                except Exception as e:
                    print(f"   Status: Error - {str(e)}")
                    extraction_errors.append(f"Marks: {str(e)}")
            else:
                print(f"\n[Step 3/3] Skipped - No semester ID provided")
            
            print("\n" + "="*70)
            if extraction_errors:
                print("DATA EXTRACTION COMPLETED WITH ERRORS")
                print("="*70)
                for error in extraction_errors:
                    print(f"   - {error}")
            else:
                print("DATA EXTRACTION COMPLETE")
                print("="*70)
            print(f"\nAll data saved to: data/")
            
            # Create/update last_state.json for watchdog
            try:
                import json
                import hashlib
                
                state = {}
                
                # Add profile hash
                if os.path.exists('data/profile-info-data.json'):
                    with open('data/profile-info-data.json', 'r', encoding='utf-8') as f:
                        profile_data = json.load(f)
                        state['profile_hash'] = hashlib.sha256(
                            json.dumps(profile_data, sort_keys=True).encode()
                        ).hexdigest()
                        state['profile_data'] = profile_data
                
                # Add attendance hash
                if os.path.exists('data/attendance-data.json'):
                    with open('data/attendance-data.json', 'r', encoding='utf-8') as f:
                        attendance_data = json.load(f)
                        state['attendance_hash'] = hashlib.sha256(
                            json.dumps(attendance_data, sort_keys=True).encode()
                        ).hexdigest()
                        state['attendance_data'] = attendance_data
                
                # Add marks hash
                if os.path.exists('data/marks-data.json'):
                    with open('data/marks-data.json', 'r', encoding='utf-8') as f:
                        marks_data = json.load(f)
                        state['marks_hash'] = hashlib.sha256(
                            json.dumps(marks_data, sort_keys=True).encode()
                        ).hexdigest()
                        state['marks_data'] = marks_data
                
                from datetime import datetime
                state['last_check'] = datetime.now().isoformat()
                
                with open('last_state.json', 'w', encoding='utf-8') as f:
                    json.dump(state, f, indent=2, ensure_ascii=False)
                
                print(f"State file updated: last_state.json")
            except Exception as e:
                print(f"Warning: Could not update state file: {e}")
            
        else:
            print("AUTHENTICATION FAILED")
            print("="*70)
            print(f"\nError Code: {error_code}")
            print(f"Error Type: {AuthError.get_error_type(error_code)}")
            print(f"Message: {message}")
            
            if error_code == AuthError.INVALID_CREDENTIALS:
                print("\nSuggestion: Please check your username and password")
            elif error_code == AuthError.INVALID_CAPTCHA:
                print("\nSuggestion: Captcha recognition failed multiple times")
            elif error_code == AuthError.MAX_ATTEMPTS:
                print("\nSuggestion: Maximum captcha attempts reached")
            elif error_code == AuthError.SERVER_CONNECTION:
                print("\nSuggestion: Could not connect to VTOP server")
            elif error_code == AuthError.ACCOUNT_LOCKED:
                print("\nSuggestion: Your account appears to be locked")
            
            if AuthError.is_retryable(error_code):
                print("\nThis error is retryable. You can try again.")
            
            sys.exit(1)
        
        print("="*70 + "\n")
        
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user")
        print("="*70 + "\n")
        sys.exit(130)
    except FileNotFoundError as e:
        print(f"\nERROR: File not found - {e}")
        print("\nInstructions:")
        print("   1. Ensure all required files are present")
        print("   2. Check that 'authentication/captcha/vellore_weights.json' exists")
        print("="*70 + "\n")
        sys.exit(1)
    except ConnectionError as e:
        print(f"\nCONNECTION ERROR: {e}")
        print("\nPossible causes:")
        print("   - No internet connection")
        print("   - VTOP server is down")
        print("   - Firewall blocking connection")
        print("="*70 + "\n")
        sys.exit(1)
    except Exception as e:
        print(f"\nUNEXPECTED ERROR: {e}")
        print("="*70 + "\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if 'auth_service' in locals():
            auth_service.logout()


def run_tests():
    """Run basic tests to verify setup"""
    print("\n" + "="*70)
    print(" "*20 + "RUNNING SETUP TESTS")
    print("="*70 + "\n")
    
    print("Test 1: Checking imports...")
    try:
        import numpy
        import PIL
        import requests
        from bs4 import BeautifulSoup
        print("All required packages imported successfully")
    except ImportError as e:
        print(f"Missing package: {e}")
        print("   Run: pip install -r requirements.txt")
        return False
    
    print("\nTest 2: Checking constants...")
    try:
        from authentication.constants import VelloreCaptchaConstants, AuthConstants
        print(f"Constants loaded")
        print(f"   - Character set: {VelloreCaptchaConstants.CHARACTER_SET}")
        print(f"   - Confidence threshold: {VelloreCaptchaConstants.CONFIDENCE_THRESHOLD}")
        print(f"   - VTOP URL: {AuthConstants.VTOP_BASE_URL}")
    except Exception as e:
        print(f"Constants error: {e}")
        return False
    
    print("\nTest 3: Checking model weights file...")
    import os
    weights_path = 'authentication/captcha/vellore_weights.json'
    if os.path.exists(weights_path):
        print("Model weights file found")
        
        size_mb = os.path.getsize(weights_path) / (1024 * 1024)
        print(f"   File size: {size_mb:.2f} MB")
        
        if size_mb < 0.1:
            print("Warning: File seems too small, might be corrupted")
        elif size_mb > 100:
            print("Warning: File seems too large, might be wrong file")
    else:
        print("Model weights file 'authentication/captcha/vellore_weights.json' not found")
        print("   Please download from: assets/ml/vellore_weights.json")
        return False
    
    print("\n" + "="*70)
    print("ALL TESTS PASSED - System is ready!")
    print("="*70 + "\n")
    return True


if __name__ == "__main__":
    import sys
    import io
    
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("\nVTOP Authentication System\n")
    
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        run_tests()
    else:
        asyncio.run(main())
