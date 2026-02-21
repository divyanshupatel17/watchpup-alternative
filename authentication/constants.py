"""
Constants for VTOP Authentication and Captcha Recognition
"""

class AuthConstants:
    """Authentication constants"""
    
    VTOP_BASE_URL = 'https://vtopcc.vit.ac.in/vtop'
    OPEN_PAGE_PATH = ''
    LOGIN_PAGE_PATH = '/login'
    CONTENT_PATH = '/content'
    
    KEY_USERNAME = 'username'
    KEY_PASSWORD = 'password'
    KEY_SEMESTER = 'semester'
    KEY_IS_SIGNED_IN = 'isVTOPSignedIn'


class VelloreCaptchaConstants:
    """Constants for Vellore captcha model configuration"""
    
    IMAGE_WIDTH = 200
    IMAGE_HEIGHT = 40
    
    CHARACTER_SET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    NUM_CLASSES = 32
    NUM_CHARACTERS = 6
    
    CONFIDENCE_THRESHOLD = 0.70
    HIGH_CONFIDENCE_THRESHOLD = 0.90
    
    WEIGHTS_ASSET_PATH = 'authentication/captcha/vellore_weights.json'
    
    @staticmethod
    def get_block_coordinates():
        """Get character block coordinates for extraction"""
        blocks = []
        for a in range(VelloreCaptchaConstants.NUM_CHARACTERS):
            x1 = (a + 1) * 25 + 2
            y1 = 7 + 5 * (a % 2) + 1
            x2 = (a + 2) * 25 + 1
            y2 = 35 - 5 * ((a + 1) % 2)
            blocks.append({
                'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                'index': a,
                'width': x2 - x1,
                'height': y2 - y1
            })
        return blocks


class AuthError:
    """Authentication error codes"""
    
    SUCCESS = 0
    
    INVALID_CAPTCHA = 1
    INVALID_CREDENTIALS = 2
    ACCOUNT_LOCKED = 3
    MAX_ATTEMPTS = 4
    UNKNOWN_ERROR = 5
    
    SERVER_CONNECTION = 51
    USER_AGENT_BLOCKED = 52
    NETWORK_TIMEOUT = 53
    HTTP_ERROR = 56
    
    OPEN_SIGN_IN = 61
    CAPTCHA_TYPE_DETECTION = 62
    CAPTCHA_IMAGE_EXTRACTION = 63
    LOGIN_SUBMISSION = 64
    
    MESSAGES = {
        SUCCESS: 'Operation completed successfully',
        INVALID_CAPTCHA: 'Invalid captcha. Please try again.',
        INVALID_CREDENTIALS: 'Invalid username or password.',
        ACCOUNT_LOCKED: 'Your account is locked.',
        MAX_ATTEMPTS: 'Maximum login attempts reached.',
        UNKNOWN_ERROR: 'An unknown error occurred.',
        SERVER_CONNECTION: 'Could not connect to server.',
        USER_AGENT_BLOCKED: 'User agent blocked. Refreshing...',
        NETWORK_TIMEOUT: 'Network timeout. Please try again.',
        HTTP_ERROR: 'HTTP error occurred.',
        OPEN_SIGN_IN: 'Error opening sign in page.',
        CAPTCHA_TYPE_DETECTION: 'Error detecting captcha type.',
        CAPTCHA_IMAGE_EXTRACTION: 'Error loading captcha image.',
        LOGIN_SUBMISSION: 'Error submitting login.',
    }
    
    @staticmethod
    def get_error_type(code):
        """Get error category for logging"""
        if code == 0:
            return 'success'
        elif 1 <= code <= 5:
            return 'login_error'
        elif 51 <= code <= 60:
            return 'connection_error'
        elif 61 <= code <= 70:
            return 'navigation_error'
        return 'unknown_error'
    
    @staticmethod
    def get_message(code):
        """Get error message"""
        return AuthError.MESSAGES.get(code, f'Error {code} occurred.')
    
    @staticmethod
    def is_retryable(code):
        """Check if error is retryable"""
        return code in [
            AuthError.INVALID_CAPTCHA,
            AuthError.SERVER_CONNECTION,
            AuthError.NETWORK_TIMEOUT
        ]
