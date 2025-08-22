# Content Moderation System

## Overview

This is a comprehensive content moderation system built with Streamlit that provides real-time analysis and filtering of inappropriate content across multiple media types including text, images, and video. The system uses machine learning and rule-based approaches to detect potentially harmful content and provides a web-based interface for content review and management.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Streamlit Web Application**: Single-page application with multiple views (Dashboard, Text Analysis, Image Analysis, Video Analysis, Content Review, Analytics)
- **Multi-page Navigation**: Sidebar-based navigation system for different analysis modules
- **Interactive Visualizations**: Uses Plotly for charts and data visualization
- **Real-time Analysis Interface**: Immediate feedback and results display for content analysis

### Backend Architecture
- **Modular Design**: Separate analyzer modules for different content types (text, image, video)
- **Session State Management**: Streamlit session state for maintaining analyzer instances and user data
- **SQLite Database**: Local database for storing analysis results and audit trails
- **File Processing**: Handles multiple file formats and byte stream processing

### Content Analysis Engines
- **Text Analyzer**: 
  - NLTK-based natural language processing
  - Rule-based inappropriate word detection
  - Spam pattern recognition
  - Sentiment analysis using TextBlob
- **Image Analyzer**: 
  - OpenCV for computer vision tasks
  - Face detection capabilities
  - Image property analysis (dimensions, color distribution)
  - Basic content filtering based on visual characteristics
- **Video Analyzer**: 
  - Frame-by-frame analysis using the image analyzer
  - Temporal sampling with configurable intervals
  - Duration-limited processing for performance

### Data Storage Solutions
- **SQLite Database**: 
  - `analysis_results` table for storing content analysis outcomes
  - `user_actions` table for audit trail and user decisions
  - Stores confidence scores, reasons, and detailed analysis metadata
- **File-based Configuration**: Inappropriate words list stored in text files for easy updates

### Security and Content Detection
- **Multi-layered Detection**: Combines rule-based and heuristic approaches
- **Confidence Scoring**: Numerical confidence levels for moderation decisions
- **Reason Tracking**: Detailed explanations for why content was flagged
- **Status Management**: Pending, approved, rejected status workflow

## External Dependencies

### Core Libraries
- **Streamlit**: Web application framework and user interface
- **Pandas**: Data manipulation and analysis
- **Plotly**: Interactive data visualization and charting
- **OpenCV (cv2)**: Computer vision and image processing
- **PIL (Pillow)**: Image processing and manipulation
- **NLTK**: Natural language processing and text analysis
- **TextBlob**: Sentiment analysis and text processing
- **NumPy**: Numerical computing for image/video processing

### Data Processing
- **SQLite3**: Built-in database for data persistence
- **UUID**: Unique identifier generation for records
- **JSON**: Data serialization for complex analysis results

### File Handling
- **BytesIO**: In-memory byte stream processing
- **Base64**: Binary data encoding for web transfer
- **Tempfile**: Temporary file management for video processing

### Machine Learning Components
- **OpenCV Cascade Classifiers**: Pre-trained models for face detection
- **NLTK Corpora**: Stopwords, tokenizers, and POS taggers for text analysis
- **TextBlob Models**: Sentiment analysis and natural language processing
