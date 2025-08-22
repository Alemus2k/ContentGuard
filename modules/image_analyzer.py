import cv2
import numpy as np
from PIL import Image, ImageStat
import io
import base64

class ImageAnalyzer:
    def __init__(self):
        """Initialize the image analyzer with OpenCV cascade classifiers."""
        self.face_cascade = None
        self.load_cascades()
        
    def load_cascades(self):
        """Load OpenCV cascade classifiers."""
        try:
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        except Exception as e:
            print(f"Warning: Could not load face cascade classifier: {e}")
    
    def analyze(self, image_bytes):
        """
        Analyze image content for inappropriate material.
        
        Args:
            image_bytes (bytes): Image data as bytes
            
        Returns:
            dict: Analysis results including appropriateness, confidence, and reasons
        """
        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                return {
                    'is_inappropriate': False,
                    'confidence_score': 0.0,
                    'reasons': ['Could not decode image'],
                    'details': {}
                }
            
            reasons = []
            scores = []
            details = {}
            
            # 1. Basic image properties analysis
            height, width = image.shape[:2]
            details['dimensions'] = f"{width}x{height}"
            details['size'] = len(image_bytes)
            
            # 2. Color analysis
            color_analysis = self.analyze_colors(image)
            details['color_analysis'] = color_analysis
            
            # Check for suspicious color patterns
            if color_analysis.get('skin_tone_ratio', 0) > 0.4:
                reasons.append("High skin tone ratio detected")
                scores.append(0.6)
            
            # 3. Face detection
            face_count = self.detect_faces(image)
            details['face_count'] = face_count
            
            if face_count > 5:
                reasons.append(f"Multiple faces detected ({face_count})")
                scores.append(0.3)
            
            # 4. Edge and texture analysis
            texture_score = self.analyze_texture(image)
            details['texture_score'] = texture_score
            
            if texture_score > 0.7:
                reasons.append("Complex texture patterns detected")
                scores.append(0.4)
            
            # 5. Brightness and contrast analysis
            brightness_contrast = self.analyze_brightness_contrast(image)
            details.update(brightness_contrast)
            
            if brightness_contrast['is_suspicious']:
                reasons.append("Suspicious brightness/contrast patterns")
                scores.append(0.3)
            
            # 6. Object detection (basic geometric shapes)
            object_analysis = self.detect_basic_objects(image)
            details.update(object_analysis)
            
            # 7. Image quality assessment
            quality_score = self.assess_image_quality(image)
            details['quality_score'] = quality_score
            
            if quality_score < 0.3:
                reasons.append("Poor image quality detected")
                scores.append(0.2)
            
            # Calculate overall confidence score
            if scores:
                confidence_score = min(max(scores), 1.0)
                is_inappropriate = confidence_score > 0.5
            else:
                confidence_score = 0.1  # Low confidence for appropriate content
                is_inappropriate = False
            
            return {
                'is_inappropriate': is_inappropriate,
                'confidence_score': confidence_score,
                'reasons': reasons,
                'details': details
            }
            
        except Exception as e:
            return {
                'is_inappropriate': False,
                'confidence_score': 0.0,
                'reasons': [f'Error analyzing image: {str(e)}'],
                'details': {}
            }
    
    def analyze_colors(self, image):
        """Analyze color composition of the image."""
        try:
            # Convert BGR to RGB for PIL
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_image)
            
            # Calculate dominant colors
            colors = pil_image.getcolors(maxcolors=256*256*256)
            if colors:
                # Sort by frequency
                colors.sort(key=lambda x: x[0], reverse=True)
                dominant_color = colors[0][1]
                
                # Convert to HSV for better skin tone detection
                hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
                
                # Define skin tone range in HSV
                lower_skin = np.array([0, 20, 70])
                upper_skin = np.array([20, 255, 255])
                
                skin_mask = cv2.inRange(hsv_image, lower_skin, upper_skin)
                skin_ratio = np.sum(skin_mask > 0) / (image.shape[0] * image.shape[1])
                
                return {
                    'dominant_color': dominant_color,
                    'skin_tone_ratio': skin_ratio,
                    'color_variety': len(colors)
                }
            else:
                return {'error': 'Could not extract colors'}
                
        except Exception as e:
            return {'error': str(e)}
    
    def detect_faces(self, image):
        """Detect faces in the image."""
        if self.face_cascade is None:
            return 0
            
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            return len(faces)
        except Exception as e:
            return 0
    
    def analyze_texture(self, image):
        """Analyze texture complexity using edge detection."""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply Canny edge detection
            edges = cv2.Canny(gray, 50, 150)
            
            # Calculate edge density
            edge_ratio = np.sum(edges > 0) / (gray.shape[0] * gray.shape[1])
            
            return edge_ratio
        except Exception as e:
            return 0.0
    
    def analyze_brightness_contrast(self, image):
        """Analyze brightness and contrast patterns."""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Calculate mean brightness
            mean_brightness = np.mean(gray) / 255.0
            
            # Calculate contrast (standard deviation)
            contrast = np.std(gray) / 255.0
            
            # Check for suspicious patterns
            is_suspicious = (mean_brightness < 0.2 and contrast > 0.5) or (mean_brightness > 0.8 and contrast < 0.1)
            
            return {
                'mean_brightness': mean_brightness,
                'contrast': contrast,
                'is_suspicious': is_suspicious
            }
        except Exception as e:
            return {
                'mean_brightness': 0.5,
                'contrast': 0.5,
                'is_suspicious': False,
                'error': str(e)
            }
    
    def detect_basic_objects(self, image):
        """Detect basic geometric objects and patterns."""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply edge detection
            edges = cv2.Canny(gray, 50, 150)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Analyze contours
            large_objects = len([c for c in contours if cv2.contourArea(c) > 1000])
            total_objects = len(contours)
            
            # Detect circles using HoughCircles
            circles = cv2.HoughCircles(
                gray,
                cv2.HOUGH_GRADIENT,
                dp=1,
                minDist=30,
                param1=50,
                param2=30,
                minRadius=10,
                maxRadius=100
            )
            
            circle_count = len(circles[0]) if circles is not None else 0
            
            return {
                'detected_objects': f"{large_objects} large objects, {total_objects} total contours",
                'large_object_count': large_objects,
                'total_contours': total_objects,
                'circle_count': circle_count
            }
            
        except Exception as e:
            return {
                'detected_objects': 'Error in object detection',
                'large_object_count': 0,
                'total_contours': 0,
                'circle_count': 0,
                'error': str(e)
            }
    
    def assess_image_quality(self, image):
        """Assess overall image quality."""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Calculate Laplacian variance (measure of focus/blur)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # Normalize to 0-1 range (higher values indicate better focus)
            quality_score = min(laplacian_var / 1000.0, 1.0)
            
            return quality_score
            
        except Exception as e:
            return 0.5  # Default medium quality
