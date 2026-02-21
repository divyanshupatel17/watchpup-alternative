"""
Data models for VTOP authentication
"""
from enum import Enum
from datetime import datetime
from typing import List, Optional


class AuthState(Enum):
    """Authentication states"""
    IDLE = "idle"
    LOADING = "loading"
    CAPTCHA_REQUIRED = "captcha_required"
    SEMESTER_SELECTION = "semester_selection"
    DATA_DOWNLOADING = "data_downloading"
    COMPLETE = "complete"
    ERROR = "error"


class CaptchaType(Enum):
    """Captcha types"""
    DEFAULT_CAPTCHA = "default_captcha"
    RE_CAPTCHA = "re_captcha"


class PageState(Enum):
    """Page states"""
    LANDING = "landing"
    LOGIN = "login"
    HOME = "home"


class CaptchaResult:
    """Result of custom captcha recognition with confidence scores"""
    
    def __init__(
        self,
        text: str,
        average_confidence: float,
        character_confidences: List[float],
        meets_threshold: bool,
        processing_time_ms: int,
        timestamp: Optional[datetime] = None
    ):
        assert len(text) == 6, 'Captcha text must be exactly 6 characters'
        assert len(character_confidences) == 6, 'Must have confidence for each character'
        assert 0.0 <= average_confidence <= 1.0, 'Confidence must be between 0 and 1'
        
        self.text = text
        self.average_confidence = average_confidence
        self.character_confidences = character_confidences
        self.meets_threshold = meets_threshold
        self.processing_time_ms = processing_time_ms
        self.timestamp = timestamp or datetime.now()
    
    @property
    def confidence_percentage(self) -> float:
        """Get confidence as percentage"""
        return self.average_confidence * 100
    
    @property
    def min_confidence(self) -> float:
        """Get minimum character confidence"""
        return min(self.character_confidences) if self.character_confidences else 0.0
    
    @property
    def max_confidence(self) -> float:
        """Get maximum character confidence"""
        return max(self.character_confidences) if self.character_confidences else 0.0
    
    @property
    def is_high_confidence(self) -> bool:
        """Check if confidence is high (>= 90%)"""
        return self.average_confidence >= 0.90
    
    @property
    def formatted_confidence(self) -> str:
        """Get formatted confidence string"""
        return f"{self.confidence_percentage:.1f}%"
    
    @property
    def character_breakdown(self) -> str:
        """Get character-by-character confidence breakdown"""
        parts = []
        for i, char in enumerate(self.text):
            conf = self.character_confidences[i] * 100
            parts.append(f"{char}:{conf:.1f}%")
        return ", ".join(parts)
    
    def __str__(self):
        return (
            f'CaptchaResult(text: "{self.text}", confidence: {self.formatted_confidence}, '
            f'threshold: {self.meets_threshold}, time: {self.processing_time_ms}ms)'
        )
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'text': self.text,
            'averageConfidence': self.average_confidence,
            'characterConfidences': self.character_confidences,
            'meetsThreshold': self.meets_threshold,
            'processingTimeMs': self.processing_time_ms,
            'timestamp': self.timestamp.isoformat(),
            'characterBreakdown': self.character_breakdown,
        }


class UserSession:
    """User session data"""
    
    def __init__(
        self,
        username: str,
        student_name: Optional[str] = None,
        registration_number: Optional[str] = None,
        semester_name: Optional[str] = None,
        semester_id: Optional[str] = None,
        login_time: Optional[datetime] = None,
        last_refresh: Optional[datetime] = None
    ):
        self.username = username
        self.student_name = student_name
        self.registration_number = registration_number
        self.semester_name = semester_name
        self.semester_id = semester_id
        self.login_time = login_time or datetime.now()
        self.last_refresh = last_refresh or datetime.now()
    
    @property
    def is_valid(self) -> bool:
        """Check if session is valid (less than 24 hours old)"""
        now = datetime.now()
        session_age = now - self.login_time
        return session_age.total_seconds() < 86400  # 24 hours
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'username': self.username,
            'studentName': self.student_name,
            'registrationNumber': self.registration_number,
            'semesterName': self.semester_name,
            'semesterID': self.semester_id,
            'loginTime': int(self.login_time.timestamp() * 1000),
            'lastRefresh': int(self.last_refresh.timestamp() * 1000),
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary"""
        return cls(
            username=data['username'],
            student_name=data.get('studentName'),
            registration_number=data.get('registrationNumber'),
            semester_name=data.get('semesterName'),
            semester_id=data.get('semesterID'),
            login_time=datetime.fromtimestamp(data['loginTime'] / 1000),
            last_refresh=datetime.fromtimestamp(data['lastRefresh'] / 1000),
        )
