"""
Neural network model for Vellore captcha character recognition
"""
import json
import numpy as np
from typing import Tuple, List
from ..constants import VelloreCaptchaConstants


class VelloreModel:
    """Neural network model for character prediction"""
    
    def __init__(self):
        self.biases = None
        self.weights = None
        self.is_loaded = False
    
    def load_model(self, weights_path: str):
        """
        Load model weights from JSON file
        
        Args:
            weights_path: Path to weights JSON file
        """
        if self.is_loaded:
            print("[VelloreModel] Model already loaded, skipping")
            return
        
        try:
            print("[VelloreModel] Loading weights from file...")
            
            with open(weights_path, 'r') as f:
                data = json.load(f)
            
            self.biases = np.array(data['biases'], dtype=np.float32)
            self.weights = np.array(data['weights'], dtype=np.float32)
            
            # Validate shapes
            if len(self.biases) != VelloreCaptchaConstants.NUM_CLASSES:
                raise ValueError(
                    f'Invalid biases length: {len(self.biases)}, '
                    f'expected {VelloreCaptchaConstants.NUM_CLASSES}'
                )
            
            input_size = self.weights.shape[0]
            output_size = self.weights.shape[1]
            
            if output_size != VelloreCaptchaConstants.NUM_CLASSES:
                raise ValueError(
                    f'Invalid weights output size: {output_size}, '
                    f'expected {VelloreCaptchaConstants.NUM_CLASSES}'
                )
            
            self.is_loaded = True
            
            print(
                f"[VelloreModel] ✓ Model loaded successfully "
                f"(input: {input_size}, output: {output_size})"
            )
            
        except Exception as e:
            print(f"[VelloreModel] ✗ Failed to load model: {e}")
            raise
    
    def predict_character(self, block_input: np.ndarray) -> Tuple[str, float]:
        """
        Predict single character from preprocessed block
        
        Args:
            block_input: Preprocessed character block (flattened array)
            
        Returns:
            Tuple of (predicted_character, confidence)
        """
        if not self.is_loaded:
            raise RuntimeError('Model not loaded. Call load_model() first.')
        
        try:
            # Compute logits
            logits = self._compute_logits(block_input)
            
            # Apply softmax
            probs = self._softmax(logits)
            
            # Find max probability
            max_idx = np.argmax(probs)
            max_prob = probs[max_idx]
            
            # Get character
            char = VelloreCaptchaConstants.CHARACTER_SET[max_idx]
            
            return (char, float(max_prob))
            
        except Exception as e:
            print(f"[VelloreModel] ✗ Prediction failed: {e}")
            raise
    
    def _compute_logits(self, input_data: np.ndarray) -> np.ndarray:
        """
        Compute logits: input · weights + biases
        
        Args:
            input_data: Input features
            
        Returns:
            Logits array
        """
        input_len = len(input_data)
        
        if input_len != self.weights.shape[0]:
            raise ValueError(
                f'Input length {input_len} does not match '
                f'weights input size {self.weights.shape[0]}'
            )
        
        # Matrix multiplication + bias
        logits = np.dot(input_data, self.weights) + self.biases
        
        return logits
    
    def _softmax(self, logits: np.ndarray) -> np.ndarray:
        """
        Softmax activation function
        
        Args:
            logits: Raw logits
            
        Returns:
            Probability distribution
        """
        # Subtract max for numerical stability
        max_logit = np.max(logits)
        exp_logits = np.exp(logits - max_logit)
        sum_exp = np.sum(exp_logits)
        
        return exp_logits / sum_exp
    
    @property
    def input_size(self) -> int:
        """Get model input size"""
        return self.weights.shape[0] if self.is_loaded else 0
    
    @property
    def output_size(self) -> int:
        """Get model output size"""
        return len(self.biases) if self.is_loaded else 0
    
    @property
    def model_info(self) -> dict:
        """Get model information"""
        if not self.is_loaded:
            return {'loaded': False}
        
        return {
            'loaded': True,
            'inputSize': self.input_size,
            'outputSize': self.output_size,
            'characterSet': VelloreCaptchaConstants.CHARACTER_SET,
            'threshold': VelloreCaptchaConstants.CONFIDENCE_THRESHOLD,
        }
    
    def dispose(self):
        """Clean up model resources"""
        self.biases = None
        self.weights = None
        self.is_loaded = False
        print("[VelloreModel] Model disposed")
