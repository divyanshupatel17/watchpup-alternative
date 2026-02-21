"""
VTOP Authentication Service
"""
import requests
from bs4 import BeautifulSoup
import base64
import os
from datetime import datetime
from typing import Optional, Tuple
from .models import AuthState, UserSession
from .captcha.captcha_solver import CustomCaptchaSolver
from .constants import AuthConstants, AuthError
import time


class AuthService:
    """Main authentication service for VTOP"""
    
    def __init__(self):
        self.session = requests.Session()
        self.captcha_solver = CustomCaptchaSolver()
        self.current_state = AuthState.IDLE
        self.user_session: Optional[UserSession] = None
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.session.verify = False
        
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        self.debug_dir = 'debug'
        os.makedirs(self.debug_dir, exist_ok=True)
    
    def _save_debug(self, filename: str, content):
        """Save debug file"""
        try:
            filepath = os.path.join(self.debug_dir, filename)
            mode = 'wb' if isinstance(content, bytes) else 'w'
            encoding = None if isinstance(content, bytes) else 'utf-8'
            with open(filepath, mode, encoding=encoding) as f:
                f.write(content)
            print(f"[DEBUG] Saved: {filepath}")
        except Exception as e:
            print(f"[DEBUG] Failed to save {filename}: {e}")
    
    async def initialize(self, weights_path: str = 'authentication/captcha/vellore_weights.json'):
        """Initialize the service"""
        print("[AuthService] Initializing...")
        await self.captcha_solver.initialize(weights_path)
        print("[AuthService] Ready")
    
    async def login(self, username: str, password: str, max_attempts: int = 3) -> Tuple[bool, int, str]:
        """
        Perform VTOP login
        
        Args:
            username: VTOP username
            password: VTOP password
            max_attempts: Maximum captcha attempts
            
        Returns:
            Tuple of (success, error_code, message)
        """
        print(f"\n{'='*60}")
        print(f"[AuthService] Starting authentication")
        print(f"[AuthService] Username: {username}")
        print(f"{'='*60}\n")
        
        self.current_state = AuthState.LOADING
        
        # Step 1: Open VTOP homepage
        print(f"[AuthService] Step 1: Connecting to VTOP...")
        response = self.session.get(f"{AuthConstants.VTOP_BASE_URL}", timeout=10)
        if response.status_code != 200:
            return False, AuthError.SERVER_CONNECTION, "Connection failed"
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self._save_debug(f'01_home_{timestamp}.html', response.text)
        print(f"[AuthService] Connected")
        
        # Step 2: POST to /vtop/prelogin/setup
        print(f"[AuthService] Step 2: Setting up session...")
        soup = BeautifulSoup(response.text, 'html.parser')
        form = soup.find('form', {'id': 'stdForm'})
        
        if form:
            form_data = {}
            for input_tag in form.find_all('input'):
                name = input_tag.get('name')
                value = input_tag.get('value', '')
                if name:
                    form_data[name] = value
            
            setup_response = self.session.post(
                f"{AuthConstants.VTOP_BASE_URL}/prelogin/setup",
                data=form_data,
                timeout=10
            )
            self._save_debug(f'02_setup_{timestamp}.html', setup_response.text)
            print(f"[AuthService] Session setup complete")
        else:
            print(f"[AuthService] No stdForm found, continuing...")
        
        # Step 3: GET login page
        print(f"[AuthService] Step 3: Opening login page...")
        login_response = self.session.get(f"{AuthConstants.VTOP_BASE_URL}/login", timeout=10)
        self._save_debug(f'03_login_{timestamp}.html', login_response.text)
        print(f"[AuthService] Login page loaded")
        
        # Captcha attempts
        for attempt in range(1, max_attempts + 1):
            print(f"\n[AuthService] Captcha Attempt {attempt}/{max_attempts}")
            
            # Step 4: Get fresh login page with captcha
            print(f"[AuthService] Step 4: Fetching captcha...")
            login_response = self.session.get(f"{AuthConstants.VTOP_BASE_URL}/login", timeout=10)
            soup = BeautifulSoup(login_response.text, 'html.parser')
            
            # Extract captcha image
            captcha_img = None
            captcha_block = soup.find('div', {'id': 'captchaBlock'})
            if captcha_block:
                captcha_img = captcha_block.find('img')
            
            if not captcha_img or not captcha_img.get('src'):
                print(f"[AuthService] No captcha found")
                continue
            
            src = captcha_img['src']
            if not src.startswith('data:image'):
                print(f"[AuthService] Invalid captcha format")
                continue
            
            # Decode base64 captcha
            match = __import__('re').match(r'data:image/[^;]+;base64,(.+)', src)
            if not match:
                print(f"[AuthService] Failed to parse captcha")
                continue
            
            image_data = base64.b64decode(match.group(1))
            print(f"[AuthService] Captcha extracted ({len(image_data)} bytes)")
            self._save_debug(f'05_captcha_{timestamp}_{attempt}.png', image_data)
            
            # Step 5: Solve captcha
            print(f"[AuthService] Step 5: Solving captcha...")
            captcha_result = await self.captcha_solver.solve_captcha(image_data)
            
            if not captcha_result or not captcha_result.meets_threshold:
                print(f"[AuthService] Low confidence captcha")
                continue
            
            captcha_text = captcha_result.text
            print(f"[AuthService] Captcha solved: \"{captcha_text}\" ({captcha_result.formatted_confidence})")
            
            # Step 6: Submit login
            print(f"[AuthService] Step 6: Submitting login...")
            
            # Parse the login form to get ALL fields
            login_form = soup.find('form', {'id': 'vtopLoginForm'})
            if not login_form:
                print(f"[AuthService] Login form not found")
                continue
            
            # Build form data from ALL form inputs
            form_data = {}
            for input_tag in login_form.find_all('input'):
                name = input_tag.get('name')
                if name:
                    value = input_tag.get('value', '')
                    form_data[name] = value
            
            # Override with our values
            form_data['username'] = username
            form_data['password'] = password
            form_data['captchaStr'] = captcha_text
            
            print(f"[AuthService] Form fields: {list(form_data.keys())}")
            print(f"[AuthService] CSRF: {form_data.get('_csrf', 'none')[:20]}...")
            
            # POST to /vtop/login
            submit_response = self.session.post(
                f"{AuthConstants.VTOP_BASE_URL}/login",
                data=form_data,
                timeout=10,
                allow_redirects=True
            )
            
            self._save_debug(f'06_response_{timestamp}_{attempt}.html', submit_response.text)
            
            print(f"[AuthService] Response URL: {submit_response.url}")
            print(f"[AuthService] Response length: {len(submit_response.text)} chars")
            
            # Check response
            response_lower = submit_response.text.lower()
            
            # Check for success
            if 'authorizedidx' in response_lower or 'authorized' in response_lower:
                print(f"[AuthService] Login successful!")
                self.current_state = AuthState.COMPLETE
                self.user_session = UserSession(username=username)
                return True, AuthError.SUCCESS, "Login successful"
            
            # Check for errors
            if 'invalid captcha' in response_lower or 'captcha mismatch' in response_lower:
                print(f"[AuthService] Invalid captcha")
                continue
            
            if 'invalid user' in response_lower or 'invalid password' in response_lower:
                print(f"[AuthService] Invalid credentials")
                return False, AuthError.INVALID_CREDENTIALS, "Invalid credentials"
            
            if 'account is locked' in response_lower:
                print(f"[AuthService] Account locked")
                return False, AuthError.ACCOUNT_LOCKED, "Account locked"
            
            # Unknown error
            print(f"[AuthService] Unknown response, retrying...")
        
        # Max attempts reached
        return False, AuthError.MAX_ATTEMPTS, "Maximum attempts reached"
    
    def logout(self):
        """Logout and clear session"""
        self.session.cookies.clear()
        self.user_session = None
        self.current_state = AuthState.IDLE
    
    def get_session_info(self):
        """Get current session information"""
        return self.user_session.to_dict() if self.user_session else None
