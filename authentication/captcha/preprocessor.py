import numpy as np
from PIL import Image
import io
from typing import List
from ..constants import VelloreCaptchaConstants


class VellorePreprocessor:
    
    @staticmethod
    def preprocess(image_bytes: bytes) -> List[List[float]]:
        image = Image.open(io.BytesIO(image_bytes))
        
        resized = image.resize(
            (VelloreCaptchaConstants.IMAGE_WIDTH, VelloreCaptchaConstants.IMAGE_HEIGHT),
            Image.Resampling.BILINEAR
        )
        
        saturation = VellorePreprocessor._extract_saturation(resized)
        sat_image = VellorePreprocessor._reshape(saturation, 40, 200)
        blocks = VellorePreprocessor._extract_blocks(sat_image)
        
        processed_blocks = []
        for block in blocks:
            processed = VellorePreprocessor._preprocess_block(block)
            processed_blocks.append(processed)
        
        return processed_blocks
    
    @staticmethod
    def _extract_saturation(image: Image.Image) -> List[float]:
        pixels = np.array(image.convert('RGB'))
        height, width, _ = pixels.shape
        
        saturation = []
        for y in range(height):
            for x in range(width):
                r, g, b = float(pixels[y, x, 0]), float(pixels[y, x, 1]), float(pixels[y, x, 2])
                
                min_val = min(r, g, b)
                max_val = max(r, g, b)
                
                if max_val > 0:
                    sat = ((max_val - min_val) * 255.0) / max_val
                else:
                    sat = 0.0
                
                saturation.append(round(sat))
        
        return saturation
    
    @staticmethod
    def _reshape(data: List[float], height: int, width: int) -> List[List[float]]:
        result = []
        for y in range(height):
            row = []
            for x in range(width):
                row.append(data[y * width + x])
            result.append(row)
        return result
    
    @staticmethod
    def _extract_blocks(sat_image: List[List[float]]) -> List[List[List[float]]]:
        blocks = []
        coords = VelloreCaptchaConstants.get_block_coordinates()
        
        for coord in coords:
            block = []
            for y in range(coord['y1'], coord['y2']):
                row = []
                for x in range(coord['x1'], coord['x2']):
                    row.append(sat_image[y][x])
                block.append(row)
            blocks.append(block)
        
        return blocks
    
    @staticmethod
    def _preprocess_block(block: List[List[float]]) -> List[float]:
        total = 0.0
        count = 0
        for row in block:
            for val in row:
                total += val
                count += 1
        
        avg = total / count if count > 0 else 0.0
        
        result = []
        for row in block:
            for val in row:
                result.append(1.0 if val > avg else 0.0)
        
        return result
