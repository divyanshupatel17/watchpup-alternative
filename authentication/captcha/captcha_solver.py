"""
Custom captcha solver combining preprocessing and neural network inference
"""
import time
from typing import Optional
from ..models import CaptchaResult
from .neural_model import VelloreModel
from .preprocessor import VellorePreprocessor
from ..constants import VelloreCaptchaConstants


class CustomCaptchaSolver:
    """Main captcha solver"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.model = VelloreModel()
            self.is_initialized = False
            self._initialized = True
    
    async def initialize(self, weights_path: str = 'authentication/captcha/vellore_weights.json'):
        """Initialize the solver (load model weights)"""
        if self.is_initialized:
            print("[CustomCaptcha] Already initialized")
            return
        
        try:
            print("[CustomCaptcha] Initializing custom captcha solver...")
            start_time = time.time()
            
            self.model.load_model(weights_path)
            self.is_initialized = True
            
            duration_ms = int((time.time() - start_time) * 1000)
            print(f"[CustomCaptcha] Custom captcha solver initialized in {duration_ms}ms")
            print(f"[CustomCaptcha] Model info: {self.model.model_info}")
            
        except Exception as e:
            print(f"[CustomCaptcha] Initialization failed: {e}")
            raise
    
    async def solve_captcha(self, image_bytes: bytes) -> Optional[CaptchaResult]:
        """Solve captcha from image bytes"""
        if not self.is_initialized:
            print("[CustomCaptcha] Not initialized, initializing now...")
            await self.initialize()
        
        start_time = time.time()
        
        try:
            print("[CustomCaptcha] Starting custom captcha recognition")
            
            # Step 1: Preprocessing
            print("[CustomCaptcha] Step 1: Preprocessing image...")
            preprocess_start = time.time()
            blocks = VellorePreprocessor.preprocess(image_bytes)
            preprocess_time = int((time.time() - preprocess_start) * 1000)
            print(f"[CustomCaptcha] Preprocessing complete in {preprocess_time}ms")
            
            if len(blocks) != VelloreCaptchaConstants.NUM_CHARACTERS:
                raise Exception(
                    f'Expected {VelloreCaptchaConstants.NUM_CHARACTERS} blocks, '
                    f'got {len(blocks)}'
                )
            
            # Step 2: Inference
            print("[CustomCaptcha] Step 2: Running neural network inference...")
            inference_start = time.time()
            
            characters = []
            confidences = []
            
            for i, block in enumerate(blocks):
                char, confidence = self.model.predict_character(block)
                characters.append(char)
                confidences.append(confidence)
                
                conf_percent = f"{confidence * 100:.1f}"
                
                if confidence >= VelloreCaptchaConstants.HIGH_CONFIDENCE_THRESHOLD:
                    emoji = "High"
                elif confidence >= VelloreCaptchaConstants.CONFIDENCE_THRESHOLD:
                    emoji = "OK"
                else:
                    emoji = "Low"
                
                print(f"[CustomCaptcha]   {emoji} Char {i + 1}: \"{char}\" (conf: {conf_percent}%)")
            
            inference_time = int((time.time() - inference_start) * 1000)
            print(f"[CustomCaptcha] Inference complete in {inference_time}ms")
            
            # Step 3: Result aggregation
            print("[CustomCaptcha] Step 3: Aggregating results...")
            
            text = ''.join(characters)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            avg_confidence = max(0.0, min(1.0, avg_confidence))
            
            meets_threshold = avg_confidence >= VelloreCaptchaConstants.CONFIDENCE_THRESHOLD
            total_time = int((time.time() - start_time) * 1000)
            
            result = CaptchaResult(
                text=text,
                average_confidence=avg_confidence,
                character_confidences=confidences,
                meets_threshold=meets_threshold,
                processing_time_ms=total_time
            )
            
            # Step 4: Logging
            if meets_threshold:
                print("[CustomCaptcha] HIGH CONFIDENCE PREDICTION")
                print(f"[CustomCaptcha]    Text: \"{text}\"")
                print(f"[CustomCaptcha]    Confidence: {result.formatted_confidence}")
                print(f"[CustomCaptcha]    Time: {total_time}ms")
                print(f"[CustomCaptcha]    Status: READY FOR AUTO-SUBMIT")
            else:
                print("[CustomCaptcha] LOW CONFIDENCE PREDICTION")
                print(f"[CustomCaptcha]    Text: \"{text}\"")
                print(f"[CustomCaptcha]    Confidence: {result.formatted_confidence}")
                print(f"[CustomCaptcha]    Time: {total_time}ms")
                print(f"[CustomCaptcha]    Status: WILL TRY FALLBACK (manual input)")
            
            return result
            
        except Exception as e:
            duration = int((time.time() - start_time) * 1000)
            print(f"[CustomCaptcha] Captcha recognition failed after {duration}ms: {e}")
            return None
    
    def get_model_info(self) -> dict:
        """Get model information"""
        return self.model.model_info
    
    def dispose(self):
        """Clean up resources"""
        self.model.dispose()
        self.is_initialized = False
        print("[CustomCaptcha] Solver disposed")


solver = CustomCaptchaSolver()
