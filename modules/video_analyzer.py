import cv2
import numpy as np
import tempfile
import os
from .image_analyzer import ImageAnalyzer

class VideoAnalyzer:
    def __init__(self):
        """Initialize the video analyzer."""
        self.image_analyzer = ImageAnalyzer()
        
    def analyze(self, video_bytes, frame_interval=3, max_duration=60):
        """
        Analyze video content for inappropriate material.
        
        Args:
            video_bytes (bytes): Video data as bytes
            frame_interval (int): Interval in seconds between frame analysis
            max_duration (int): Maximum duration to analyze in seconds
            
        Returns:
            dict: Analysis results including appropriateness, confidence, and reasons
        """
        # Save video to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
            temp_file.write(video_bytes)
            temp_path = temp_file.name
        
        try:
            return self._analyze_video_file(temp_path, frame_interval, max_duration)
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except Exception:
                pass
    
    def _analyze_video_file(self, video_path, frame_interval, max_duration):
        """Analyze video file frame by frame."""
        try:
            # Open video file
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                return {
                    'is_inappropriate': False,
                    'confidence_score': 0.0,
                    'reasons': ['Could not open video file'],
                    'details': {}
                }
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0
            
            # Limit analysis duration
            actual_duration = min(duration, max_duration)
            frame_step = max(1, int(fps * frame_interval))
            
            frame_analyses = []
            inappropriate_frames = 0
            total_confidence = 0
            
            frame_num = 0
            while cap.isOpened() and frame_num < actual_duration * fps:
                # Set frame position
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = cap.read()
                
                if not ret:
                    break
                
                # Convert frame to bytes for analysis
                _, buffer = cv2.imencode('.jpg', frame)
                frame_bytes = buffer.tobytes()
                
                # Analyze frame using image analyzer
                frame_result = self.image_analyzer.analyze(frame_bytes)
                
                frame_analysis = {
                    'frame_number': frame_num,
                    'timestamp': frame_num / fps,
                    'is_inappropriate': frame_result['is_inappropriate'],
                    'confidence_score': frame_result['confidence_score'],
                    'reasons': frame_result['reasons']
                }
                
                frame_analyses.append(frame_analysis)
                
                if frame_result['is_inappropriate']:
                    inappropriate_frames += 1
                
                total_confidence += frame_result['confidence_score']
                
                # Move to next frame
                frame_num += frame_step
            
            cap.release()
            
            # Calculate overall results
            total_analyzed_frames = len(frame_analyses)
            
            if total_analyzed_frames == 0:
                return {
                    'is_inappropriate': False,
                    'confidence_score': 0.0,
                    'reasons': ['No frames could be analyzed'],
                    'details': {}
                }
            
            # Calculate metrics
            inappropriate_ratio = inappropriate_frames / total_analyzed_frames
            avg_confidence = total_confidence / total_analyzed_frames
            
            # Determine if video is inappropriate
            # If more than 30% of frames are inappropriate, flag the video
            is_inappropriate = inappropriate_ratio > 0.3 or (inappropriate_frames > 0 and avg_confidence > 0.7)
            
            # Adjust confidence based on inappropriate frame ratio
            if is_inappropriate:
                confidence_score = min(avg_confidence + (inappropriate_ratio * 0.3), 1.0)
            else:
                confidence_score = avg_confidence * 0.5  # Lower confidence for appropriate content
            
            # Collect reasons
            reasons = []
            if inappropriate_frames > 0:
                reasons.append(f"{inappropriate_frames}/{total_analyzed_frames} frames flagged as inappropriate")
            
            if inappropriate_ratio > 0.5:
                reasons.append("High proportion of inappropriate content")
            
            # Add specific reasons from frame analyses
            all_frame_reasons = []
            for frame in frame_analyses:
                if frame['is_inappropriate']:
                    all_frame_reasons.extend(frame['reasons'])
            
            # Get unique reasons
            unique_reasons = list(set(all_frame_reasons))
            reasons.extend(unique_reasons[:3])  # Add up to 3 unique frame reasons
            
            return {
                'is_inappropriate': is_inappropriate,
                'confidence_score': confidence_score,
                'reasons': reasons,
                'details': {
                    'duration': duration,
                    'fps': fps,
                    'total_frames': total_frames,
                    'analyzed_frames': total_analyzed_frames,
                    'inappropriate_frames': inappropriate_frames,
                    'inappropriate_ratio': inappropriate_ratio,
                    'avg_confidence': avg_confidence,
                    'frame_analyses': frame_analyses[:10]  # Include first 10 frame analyses
                }
            }
            
        except Exception as e:
            return {
                'is_inappropriate': False,
                'confidence_score': 0.0,
                'reasons': [f'Error analyzing video: {str(e)}'],
                'details': {}
            }
    
    def extract_frames(self, video_path, output_dir, frame_interval=5):
        """
        Extract frames from video for manual review.
        
        Args:
            video_path (str): Path to video file
            output_dir (str): Directory to save extracted frames
            frame_interval (int): Interval in seconds between frames
            
        Returns:
            list: List of extracted frame file paths
        """
        try:
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_step = max(1, int(fps * frame_interval))
            
            frame_paths = []
            frame_num = 0
            saved_frame_count = 0
            
            while cap.isOpened():
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = cap.read()
                
                if not ret:
                    break
                
                # Save frame
                frame_filename = f"frame_{saved_frame_count:04d}.jpg"
                frame_path = os.path.join(output_dir, frame_filename)
                cv2.imwrite(frame_path, frame)
                
                frame_paths.append(frame_path)
                saved_frame_count += 1
                frame_num += frame_step
            
            cap.release()
            return frame_paths
            
        except Exception as e:
            print(f"Error extracting frames: {e}")
            return []
    
    def get_video_metadata(self, video_path):
        """
        Extract metadata from video file.
        
        Args:
            video_path (str): Path to video file
            
        Returns:
            dict: Video metadata
        """
        try:
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                return {}
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = frame_count / fps if fps > 0 else 0
            
            cap.release()
            
            return {
                'fps': fps,
                'frame_count': frame_count,
                'width': width,
                'height': height,
                'duration': duration,
                'resolution': f"{width}x{height}"
            }
            
        except Exception as e:
            return {'error': str(e)}
