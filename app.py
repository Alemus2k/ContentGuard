import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
from io import BytesIO
import base64

# Import custom modules
from modules.text_analyzer import TextAnalyzer
from modules.image_analyzer import ImageAnalyzer
from modules.video_analyzer import VideoAnalyzer
from modules.data_manager import DataManager
from modules.utils import get_confidence_color, format_timestamp
from modules.input_validator import (
    sanitize_text, validate_text_input, validate_image_upload,
    validate_video_upload, validate_batch_text, sanitize_filename
)
from modules.rate_limiter import RateLimiter

def load_css():
    st.markdown("""
    <style>
    .stApp {
        background: #ffffff;
    }

    .metric-card {
        background: #ffffff !important;
        color: #111 !important;
        padding: 1.5rem;
        border-radius: 4px;
        border: 1px solid #e0e0e0;
        margin: 0.5rem 0;
    }

    .metric-card h4, .metric-card h3, .metric-card h2,
    .metric-card p, .metric-card span, .metric-card div {
        color: #111 !important;
    }

    .status-badge {
        padding: 0.25rem 0.75rem;
        border-radius: 4px;
        font-size: 0.875rem;
        font-weight: 600;
        text-align: center;
        display: inline-block;
        margin: 0.25rem;
    }

    .status-appropriate {
        background: #4CAF50;
        color: white;
    }

    .status-inappropriate {
        background: #111;
        color: white;
    }

    .status-pending {
        background: #757575;
        color: white;
    }

    .stButton > button,
    div[data-testid="stButton"] > button {
        background: #4CAF50 !important;
        background-color: #4CAF50 !important;
        color: #ffffff !important;
        border: 1px solid #4CAF50 !important;
        border-radius: 4px !important;
        padding: 0.5rem 1.5rem !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        box-shadow: none !important;
        cursor: pointer !important;
    }

    .stButton > button:hover,
    div[data-testid="stButton"] > button:hover {
        background: #388E3C !important;
        background-color: #388E3C !important;
        color: #ffffff !important;
        border-color: #388E3C !important;
    }

    .stButton > button:focus,
    div[data-testid="stButton"] > button:focus {
        background: #4CAF50 !important;
        color: #ffffff !important;
        outline: none !important;
        border-color: #4CAF50 !important;
    }

    .stButton > button span,
    div[data-testid="stButton"] > button span,
    .stButton > button p,
    div[data-testid="stButton"] > button p {
        color: #ffffff !important;
        font-weight: 600 !important;
    }

    .uploadedFile {
        border: 2px dashed #4CAF50;
        border-radius: 4px;
        padding: 2rem;
        text-align: center;
    }

    .stProgress > div > div > div {
        background: #4CAF50;
        border-radius: 4px;
    }

    .main-header {
        color: #111;
        font-size: 2.5rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 1.5rem;
    }

    .section-header {
        color: #111;
        font-size: 1.5rem;
        font-weight: 700;
        margin: 1.5rem 0 1rem 0;
    }

    .metric-container {
        background: white;
        border-radius: 4px;
        padding: 1.5rem;
        border: 1px solid #e0e0e0;
        border-left: 4px solid #4CAF50;
        margin: 1rem 0;
    }

    .confidence-high { color: #111; font-weight: bold; }
    .confidence-medium { color: #757575; font-weight: bold; }
    .confidence-low { color: #4CAF50; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# Initialize session state
if 'data_manager' not in st.session_state:
    st.session_state.data_manager = DataManager()
if 'text_analyzer' not in st.session_state:
    st.session_state.text_analyzer = TextAnalyzer()
if 'image_analyzer' not in st.session_state:
    st.session_state.image_analyzer = ImageAnalyzer()
if 'video_analyzer' not in st.session_state:
    st.session_state.video_analyzer = VideoAnalyzer()
if 'rate_limiter' not in st.session_state:
    st.session_state.rate_limiter = RateLimiter(max_requests=20, window_seconds=60)

def main():
    st.set_page_config(
        page_title="Content Moderation System",
        page_icon="CM",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Load custom CSS
    load_css()
    
    st.markdown('<h1 class="main-header">Content Moderation System</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p style="text-align: center; font-size: 1.1rem; color: #555; margin-bottom: 2rem;">'
        'Real-time analysis and filtering of inappropriate content across text, images, and video'
        '</p>', 
        unsafe_allow_html=True
    )
    
    st.sidebar.markdown('<h2 style="text-align: center; margin-bottom: 1.5rem; font-weight: 700;">Navigation</h2>', unsafe_allow_html=True)
    
    pages = {
        "Dashboard": "Dashboard",
        "Text Analysis": "Text Analysis", 
        "Image Analysis": "Image Analysis",
        "Video Analysis": "Video Analysis",
        "Content Review": "Content Review",
        "Analytics": "Analytics"
    }
    
    page = None
    for page_name in pages.keys():
        if st.sidebar.button(page_name, key=f"nav_{page_name}", use_container_width=True):
            st.session_state.current_page = page_name
    
    # Get current page from session state or default to Dashboard
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Dashboard"
    
    current_page = st.session_state.current_page
    
    # Add some spacing
    st.sidebar.markdown("<br><br>", unsafe_allow_html=True)
    
    recent_data = st.session_state.data_manager.get_recent_analysis(hours=24)
    if not recent_data.empty:
        st.sidebar.markdown("---")
        st.sidebar.markdown("**Quick Stats (24h)**")
        total_items = len(recent_data)
        flagged_items = len(recent_data[recent_data['is_inappropriate'] == True])
        st.sidebar.metric("Total Items", total_items)
        st.sidebar.metric("Flagged Items", flagged_items)
        if total_items > 0:
            percentage = (flagged_items / total_items) * 100
            st.sidebar.metric("Flag Rate", f"{percentage:.1f}%")
    
    # Route to the selected page
    if current_page == "Dashboard":
        show_dashboard()
    elif current_page == "Text Analysis":
        show_text_analysis()
    elif current_page == "Image Analysis":
        show_image_analysis()
    elif current_page == "Video Analysis":
        show_video_analysis()
    elif current_page == "Content Review":
        show_content_review()
    elif current_page == "Analytics":
        show_analytics()

def show_dashboard():
    st.markdown('<h2 class="section-header"> Real-time Moderation Dashboard</h2>', unsafe_allow_html=True)
    
    # Get recent analysis data
    recent_data = st.session_state.data_manager.get_recent_analysis(hours=24)
    
    if recent_data.empty:
        st.markdown(
            '<div style="background: #f5f5f5; padding: 2rem; border-radius: 4px; text-align: center; color: #111; margin: 2rem 0; border: 1px solid #e0e0e0;">'
            '<h3> Welcome to Your Content Moderation Dashboard!</h3>'
            '<p>No recent analysis data available. Start analyzing content using the navigation menu to see your metrics come to life.</p>'
            '</div>', 
            unsafe_allow_html=True
        )
        
        # Show getting started cards
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(
                '<div class="metric-card">'
                '<h4> Analyze Text</h4>'
                '<p>Start by analyzing text content for inappropriate language, spam, and harmful content.</p>'
                '</div>', 
                unsafe_allow_html=True
            )
        
        with col2:
            st.markdown(
                '<div class="metric-card">'
                '<h4> Analyze Images</h4>'
                '<p>Upload and analyze images for inappropriate visual content using computer vision.</p>'
                '</div>', 
                unsafe_allow_html=True
            )
        
        with col3:
            st.markdown(
                '<div class="metric-card">'
                '<h4> Analyze Videos</h4>'
                '<p>Process video content frame-by-frame for comprehensive moderation analysis.</p>'
                '</div>', 
                unsafe_allow_html=True
            )
        return
    
    # Enhanced key metrics with modern cards
    st.markdown('<h3 style="margin-bottom: 1.5rem;"> Key Metrics (Last 24 Hours)</h3>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_items = len(recent_data)
        st.markdown(
            f'<div class="metric-container">'
            f'<h3 style="color: #4CAF50; margin: 0;"> {total_items}</h3>'
            f'<p style="margin: 0; color: #666;">Total Items Analyzed</p>'
            f'</div>', 
            unsafe_allow_html=True
        )
    
    with col2:
        flagged_items = len(recent_data[recent_data['is_inappropriate'] == True])
        percentage = (flagged_items/total_items*100) if total_items > 0 else 0
        st.markdown(
            f'<div class="metric-container">'
            f'<h3 style="color: #f44336; margin: 0;"> {flagged_items}</h3>'
            f'<p style="margin: 0; color: #666;">Flagged Items ({percentage:.1f}%)</p>'
            f'</div>', 
            unsafe_allow_html=True
        )
    
    with col3:
        avg_confidence = recent_data['confidence_score'].mean()
        confidence_display = f"{avg_confidence*100:.1f}%" if not pd.isna(avg_confidence) else "N/A"
        confidence_color = "#4CAF50" if avg_confidence < 0.5 else "#ff9800" if avg_confidence < 0.7 else "#f44336"
        st.markdown(
            f'<div class="metric-container">'
            f'<h3 style="color: {confidence_color}; margin: 0;"> {confidence_display}</h3>'
            f'<p style="margin: 0; color: #666;">Average Confidence</p>'
            f'</div>', 
            unsafe_allow_html=True
        )
    
    with col4:
        pending_review = len(recent_data[recent_data['status'] == 'pending'])
        st.markdown(
            f'<div class="metric-container">'
            f'<h3 style="color: #ff9800; margin: 0;"> {pending_review}</h3>'
            f'<p style="margin: 0; color: #666;">Pending Review</p>'
            f'</div>', 
            unsafe_allow_html=True
        )
    
    # Enhanced Charts with modern styling
    st.markdown('<h3 style="margin: 2rem 0 1rem 0;"> Analysis Overview</h3>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.subheader(" Content Type Distribution")
        type_counts = recent_data['content_type'].value_counts()
        if not type_counts.empty:
            fig = px.pie(
                values=type_counts.values, 
                names=type_counts.index, 
                title="Content Type Distribution",
                color_discrete_sequence=['#4CAF50', '#111111', '#757575', '#388E3C', '#999999']
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='#111111',
                title_font_size=16
            )
            st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.subheader(" Analysis Results")
        result_counts = recent_data['is_inappropriate'].value_counts()
        if not result_counts.empty:
            labels = ['Appropriate' if not x else 'Inappropriate' for x in result_counts.index]
            colors = ['#4CAF50' if 'Appropriate' in label else '#f44336' for label in labels]
            fig = px.bar(
                x=labels, 
                y=result_counts.values, 
                title="Content Appropriateness",
                color=labels,
                color_discrete_map={'Appropriate': '#4CAF50', 'Inappropriate': '#111111'}
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='#111111',
                title_font_size=16,
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Recent flagged content with modern cards
    st.markdown('<h3 style="margin: 2rem 0 1rem 0;"> Recent Flagged Content</h3>', unsafe_allow_html=True)
    flagged_data = recent_data[recent_data['is_inappropriate'] == True].head(5)
    
    if not flagged_data.empty:
        for _, item in flagged_data.iterrows():
            confidence_color = get_confidence_color(item['confidence_score'])
            confidence_class = "high" if item['confidence_score'] >= 0.7 else "medium" if item['confidence_score'] >= 0.4 else "low"
            
            with st.expander(
                f" {item['content_type'].title()} Content - "
                f"Confidence: {item['confidence_score']*100:.1f}% - "
                f"{format_timestamp(item['timestamp'])}"
            ):
                # Create a modern card layout
                st.markdown(
                    f'<div style="background: #ffffff; '
                    f'border-left: 5px solid {confidence_color}; padding: 1.5rem; border-radius: 4px; margin: 1rem 0;">',
                    unsafe_allow_html=True
                )
                
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    if item['content_type'] == 'text':
                        content_preview = str(item['content'])[:300] + "..." if len(str(item['content'])) > 300 else str(item['content'])
                        st.markdown(f"** Content Preview:**")
                        st.text_area("Content", content_preview, height=100, key=f"preview_{item['id']}")
                    else:
                        st.markdown(f"** File:** `{item.get('filename', 'Unknown')}`")
                    
                    if item['reasons']:
                        st.markdown("** Flagging Reasons:**")
                        for reason in item['reasons']:
                            st.markdown(f"• {reason}")
                    else:
                        st.markdown("**ℹ Reasons:** No specific issues detected")
                
                with col2:
                    # Status badge
                    status_class = f"status-{item['status']}"
                    st.markdown(
                        f'<div class="status-badge {status_class}">{item["status"].title()}</div>',
                        unsafe_allow_html=True
                    )
                    
                    # Confidence score with color
                    st.markdown(
                        f'<p><strong> Confidence:</strong> '
                        f'<span class="confidence-{confidence_class}">{item["confidence_score"]*100:.1f}%</span></p>',
                        unsafe_allow_html=True
                    )
                    
                    # Timestamp
                    st.markdown(f"** Analyzed:** {format_timestamp(item['timestamp'])}")
                
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="background: #f5f5f5; '
            'padding: 2rem; border-radius: 4px; text-align: center; color: #111; margin: 1rem 0;">'
            '<h4> Great News!</h4>'
            '<p>No flagged content in the last 24 hours. Your moderation system is keeping things clean!</p>'
            '</div>',
            unsafe_allow_html=True
        )

def show_text_analysis():
    st.markdown('<h2 class="section-header"> Text Content Analysis</h2>', unsafe_allow_html=True)
    
    # Modern input method selection with tabs
    tab1, tab2, tab3 = st.tabs([" Type/Paste Text", " Upload File", " Batch Analysis"])
    
    with tab1:
        show_text_input_tab()
    
    with tab2:
        show_file_upload_tab()
    
    with tab3:
        show_batch_analysis_tab()

def show_text_input_tab():
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.subheader(" Enter Text to Analyze")
    text_content = st.text_area(
        "Enter text to analyze:", 
        height=200, 
        placeholder="Type or paste your content here...",
        help="Enter any text content you want to check for inappropriate material"
    )
    
    col1, col2, col3 = st.columns([1, 1, 2])
    with col2:
        analyze_button = st.button(" Analyze Text", use_container_width=True, type="primary")
    
    if analyze_button and text_content:
        valid, errors = validate_text_input(text_content)
        if not valid:
            for error in errors:
                st.error(f"Validation error: {error}")
        elif not st.session_state.rate_limiter.is_allowed("text_analysis"):
            status = st.session_state.rate_limiter.get_status("text_analysis")
            st.warning(f"Rate limit reached. Please wait {status['reset_seconds']}s before trying again.")
        else:
            sanitized_content = sanitize_text(text_content)
            with st.spinner("🤖 Analyzing text content..."):
                result = st.session_state.text_analyzer.analyze(sanitized_content)
                
                st.session_state.data_manager.store_analysis_result(
                    content_type='text',
                    content=sanitized_content,
                    is_inappropriate=result['is_inappropriate'],
                    confidence_score=result['confidence_score'],
                    reasons=result['reasons']
                )
                
                display_text_results(result, sanitized_content)
    
    st.markdown('</div>', unsafe_allow_html=True)

def show_file_upload_tab():
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.subheader(" Upload Text File")
    uploaded_file = st.file_uploader(
        "Choose a text file", 
        type=['txt', 'md', 'csv'],
        help="Upload a text file (.txt, .md, .csv) to analyze its content"
    )
    
    if uploaded_file:
        st.success(f" File uploaded: {uploaded_file.name}")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        with col2:
            analyze_button = st.button(" Analyze File", use_container_width=True, type="primary")
        
        if analyze_button:
            if not st.session_state.rate_limiter.is_allowed("text_analysis"):
                status = st.session_state.rate_limiter.get_status("text_analysis")
                st.warning(f"Rate limit reached. Please wait {status['reset_seconds']}s before trying again.")
            else:
                try:
                    content = uploaded_file.read().decode('utf-8')
                    safe_filename = sanitize_filename(uploaded_file.name)
                    valid, errors = validate_text_input(content)
                    if not valid:
                        for error in errors:
                            st.error(f"Validation error: {error}")
                    else:
                        sanitized_content = sanitize_text(content)
                        with st.spinner("🤖 Analyzing file content..."):
                            result = st.session_state.text_analyzer.analyze(sanitized_content)
                            
                            st.session_state.data_manager.store_analysis_result(
                                content_type='text',
                                content=sanitized_content,
                                is_inappropriate=result['is_inappropriate'],
                                confidence_score=result['confidence_score'],
                                reasons=result['reasons'],
                                filename=safe_filename
                            )
                            
                            display_text_results(result, sanitized_content, safe_filename)
                except Exception as e:
                    st.error(f" Error processing file: {str(e)}")
    
    st.markdown('</div>', unsafe_allow_html=True)

def show_batch_analysis_tab():
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.subheader(" Batch Text Analysis")
    batch_text = st.text_area(
        "Enter multiple texts (one per line):", 
        height=300,
        help="Enter multiple text entries, one per line, for batch analysis"
    )
    
    col1, col2, col3 = st.columns([1, 1, 2])
    with col2:
        analyze_button = st.button(" Analyze Batch", use_container_width=True, type="primary")
    
    if analyze_button and batch_text:
        if not st.session_state.rate_limiter.is_allowed("batch_analysis"):
            status = st.session_state.rate_limiter.get_status("batch_analysis")
            st.warning(f"Rate limit reached. Please wait {status['reset_seconds']}s before trying again.")
        else:
            valid, errors, sanitized_lines = validate_batch_text(batch_text)
            if not valid:
                for error in errors:
                    st.error(f"Validation error: {error}")
            elif sanitized_lines:
                texts = sanitized_lines
                st.success(f" Processing {len(texts)} text entries...")
                progress_bar = st.progress(0)
                results = []
                
                for i, text in enumerate(texts):
                    result = st.session_state.text_analyzer.analyze(text)
                    results.append({
                        'text': text[:100] + '...' if len(text) > 100 else text,
                        'inappropriate': ' Yes' if result['is_inappropriate'] else ' No',
                        'confidence': f"{result['confidence_score']*100:.1f}%",
                        'reasons': ', '.join(result['reasons']) if result['reasons'] else 'None'
                    })
                    
                    st.session_state.data_manager.store_analysis_result(
                        content_type='text',
                        content=text,
                        is_inappropriate=result['is_inappropriate'],
                        confidence_score=result['confidence_score'],
                        reasons=result['reasons']
                    )
                    
                    progress_bar.progress((i + 1) / len(texts))
                
                st.subheader(" Batch Analysis Results")
                df = pd.DataFrame(results)
                st.dataframe(df, use_container_width=True)
                
                inappropriate_count = sum(1 for r in results if '' in r['inappropriate'])
                col1, col2, col3 = st.columns(3)
                with col2:
                    st.metric(" Flagged Items", f"{inappropriate_count}/{len(results)}")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # This content has been moved to separate tab functions above

def display_text_results(result, content, filename=None):
    st.markdown('<h3 style="margin: 1.5rem 0;"> Analysis Results</h3>', unsafe_allow_html=True)
    
    # Main result card
    confidence_color = get_confidence_color(result['confidence_score'])
    status_emoji = "" if result['is_inappropriate'] else ""
    status_text = "Inappropriate" if result['is_inappropriate'] else "Appropriate"
    status_bg = "#f5f5f5" if result['is_inappropriate'] else "#f5f5f5"
    
    st.markdown(
        f'<div style="background: {status_bg}; padding: 2rem; border-radius: 4px; margin: 1rem 0; border-left: 5px solid {confidence_color};">'
        f'<div style="display: flex; justify-content: space-between; align-items: center;">'
        f'<h2 style="margin: 0; color: #111;">{status_emoji} {status_text}</h2>'
        f'<div style="text-align: right;">'
        f'<h3 style="margin: 0; color: {confidence_color};">Confidence: {result["confidence_score"]*100:.1f}%</h3>'
        f'</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.subheader(" Content Information")
        
        if filename:
            st.markdown(f"** File:** `{filename}`")
        
        st.markdown(f"** Word Count:** {len(content.split())}")
        st.markdown(f"** Character Count:** {len(content)}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.subheader(" Detection Reasons")
        
        if result['reasons']:
            for reason in result['reasons']:
                st.markdown(f"• {reason}")
        else:
            st.markdown(" No specific issues detected")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Detailed analysis with enhanced styling
    if result.get('details'):
        st.markdown('<h4 style="margin: 1.5rem 0 1rem 0;"> Detailed Analysis</h4>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            details = result['details']
            
            if details.get('flagged_words'):
                st.subheader(" Flagged Words")
                for word in details['flagged_words']:
                    st.markdown(f'<span style="background: #e0e0e0; padding: 0.25rem 0.5rem; border-radius: 5px; margin: 0.25rem;">{word}</span>', unsafe_allow_html=True)
            else:
                st.subheader(" Flagged Words")
                st.markdown("None detected")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            if details.get('sentiment'):
                sentiment = details['sentiment']
                sentiment_color = "#4CAF50" if sentiment['label'] == 'positive' else "#f44336" if sentiment['label'] == 'negative' else "#ff9800"
                st.subheader(" Sentiment Analysis")
                st.markdown(f'<div style="background: {sentiment_color}; color: white; padding: 0.5rem; border-radius: 5px; text-align: center;">'
                           f'{sentiment["label"].title()}<br>Score: {sentiment["polarity"]:.2f}</div>', unsafe_allow_html=True)
            else:
                st.subheader(" Sentiment")
                st.markdown("Not analyzed")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.subheader(" Additional Metrics")
            if details.get('caps_ratio'):
                caps_percentage = details['caps_ratio'] * 100
                st.markdown(f"**Caps Ratio:** {caps_percentage:.1f}%")
            if details.get('repetition_score'):
                st.markdown(f"**Repetition Score:** {details['repetition_score']:.2f}")
            if details.get('spam_score'):
                st.markdown(f"**Spam Score:** {details['spam_score']:.2f}")
            st.markdown('</div>', unsafe_allow_html=True)

def show_image_analysis():
    st.markdown('<h2 class="section-header"> Image Content Analysis</h2>', unsafe_allow_html=True)
    
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.subheader(" Upload Image for Analysis")
    uploaded_file = st.file_uploader(
        "Choose an image file", 
        type=['png', 'jpg', 'jpeg', 'gif', 'bmp'],
        help="Upload an image file to analyze for inappropriate visual content"
    )
    
    if uploaded_file:
        # Display image in a modern layout
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.image(uploaded_file, caption=f" {uploaded_file.name}", use_column_width=True)
        
        with col2:
            st.markdown(
                f'<div style="background: #f5f5f5; padding: 1.5rem; border-radius: 4px; border: 1px solid #e0e0e0;">'
                f'<h4> Image Info</h4>'
                f'<p><strong>Filename:</strong> {uploaded_file.name}</p>'
                f'<p><strong>Size:</strong> {uploaded_file.size / 1024:.1f} KB</p>'
                f'<p><strong>Type:</strong> {uploaded_file.type}</p>'
                f'</div>',
                unsafe_allow_html=True
            )
            
            st.markdown('<br>', unsafe_allow_html=True)
            analyze_button = st.button(" Analyze Image", use_container_width=True, type="primary")
        
        if analyze_button:
            valid, errors = validate_image_upload(uploaded_file)
            if not valid:
                for error in errors:
                    st.error(f"Validation error: {error}")
            elif not st.session_state.rate_limiter.is_allowed("image_analysis"):
                status = st.session_state.rate_limiter.get_status("image_analysis")
                st.warning(f"Rate limit reached. Please wait {status['reset_seconds']}s before trying again.")
            else:
                safe_filename = sanitize_filename(uploaded_file.name)
                with st.spinner("🤖 Analyzing image content..."):
                    image_bytes = uploaded_file.read()
                    uploaded_file.seek(0)
                    
                    result = st.session_state.image_analyzer.analyze(image_bytes)
                    
                    st.session_state.data_manager.store_analysis_result(
                        content_type='image',
                        content=f"Image file: {safe_filename}",
                        is_inappropriate=result['is_inappropriate'],
                        confidence_score=result['confidence_score'],
                        reasons=result['reasons'],
                        filename=safe_filename
                    )
                    
                    display_image_results(result, safe_filename)
    
    st.markdown('</div>', unsafe_allow_html=True)

def display_image_results(result, filename):
    st.markdown('<h3 style="margin: 1.5rem 0;"> Analysis Results</h3>', unsafe_allow_html=True)
    
    # Main result card
    confidence_color = get_confidence_color(result['confidence_score'])
    status_emoji = "" if result['is_inappropriate'] else ""
    status_text = "Inappropriate" if result['is_inappropriate'] else "Appropriate"
    status_bg = "#f5f5f5" if result['is_inappropriate'] else "#f5f5f5"
    
    st.markdown(
        f'<div style="background: {status_bg}; padding: 2rem; border-radius: 4px; margin: 1rem 0; border-left: 5px solid {confidence_color};">'
        f'<div style="display: flex; justify-content: space-between; align-items: center;">'
        f'<h2 style="margin: 0; color: #111;">{status_emoji} {status_text}</h2>'
        f'<div style="text-align: right;">'
        f'<h3 style="margin: 0; color: {confidence_color};">Confidence: {result["confidence_score"]*100:.1f}%</h3>'
        f'</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.subheader(" Image Information")
        st.markdown(f"** Filename:** `{filename}`")
        
        if result['reasons']:
            st.subheader(" Detection Reasons")
            for reason in result['reasons']:
                st.markdown(f"• {reason}")
        else:
            st.markdown(" No specific issues detected")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        if result.get('details'):
            details = result['details']
            st.subheader(" Technical Analysis")
            
            if details.get('dimensions'):
                st.markdown(f"** Dimensions:** {details['dimensions']}")
            
            if details.get('face_count') is not None:
                face_emoji = "" if details['face_count'] > 0 else ""
                st.markdown(f"**{face_emoji} Faces Detected:** {details['face_count']}")
            
            if details.get('quality_score'):
                quality = details['quality_score']
                quality_text = "High" if quality > 0.7 else "Medium" if quality > 0.4 else "Low"
                st.markdown(f"** Image Quality:** {quality_text} ({quality:.2f})")
            
            if details.get('color_analysis'):
                st.markdown(f"** Color Analysis:** Available")
        
        st.markdown('</div>', unsafe_allow_html=True)

def show_video_analysis():
    st.markdown('<h2 class="section-header"> Video Content Analysis</h2>', unsafe_allow_html=True)
    
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.subheader(" Upload Video for Analysis")
    uploaded_file = st.file_uploader(
        "Choose a video file", 
        type=['mp4', 'avi', 'mov', 'mkv'],
        help="Upload a video file to analyze frame-by-frame for inappropriate content"
    )
    
    if uploaded_file:
        # Display video and info in modern layout
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.video(uploaded_file)
        
        with col2:
            st.markdown(
                f'<div style="background: #f5f5f5; padding: 1.5rem; border-radius: 4px; border: 1px solid #e0e0e0; color: #111;">'
                f'<h4> Video Info</h4>'
                f'<p><strong>Filename:</strong> {uploaded_file.name}</p>'
                f'<p><strong>Size:</strong> {uploaded_file.size / (1024*1024):.1f} MB</p>'
                f'<p><strong>Type:</strong> {uploaded_file.type}</p>'
                f'</div>',
                unsafe_allow_html=True
            )
        
        # Analysis configuration with modern styling
        st.markdown('<h4 style="margin: 1.5rem 0 1rem 0;"> Analysis Configuration</h4>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            frame_interval = st.slider(
                " Frame Interval (seconds)", 
                1, 10, 3,
                help="How often to analyze frames (smaller = more thorough but slower)"
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            max_duration = st.slider(
                " Max Duration (seconds)", 
                10, 300, 60,
                help="Maximum video duration to analyze (longer videos take more time)"
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown('<br>', unsafe_allow_html=True)
            analyze_button = st.button(" Analyze Video", use_container_width=True, type="primary")
            st.markdown('</div>', unsafe_allow_html=True)
        
        if analyze_button:
            valid, errors = validate_video_upload(uploaded_file)
            if not valid:
                for error in errors:
                    st.error(f"Validation error: {error}")
            elif not st.session_state.rate_limiter.is_allowed("video_analysis"):
                status = st.session_state.rate_limiter.get_status("video_analysis")
                st.warning(f"Rate limit reached. Please wait {status['reset_seconds']}s before trying again.")
            else:
                safe_filename = sanitize_filename(uploaded_file.name)
                with st.spinner("🤖 Analyzing video content... This may take a while."):
                    video_bytes = uploaded_file.read()
                    
                    result = st.session_state.video_analyzer.analyze(
                        video_bytes, 
                        frame_interval=frame_interval,
                        max_duration=max_duration
                    )
                    
                    st.session_state.data_manager.store_analysis_result(
                        content_type='video',
                        content=f"Video file: {safe_filename}",
                        is_inappropriate=result['is_inappropriate'],
                        confidence_score=result['confidence_score'],
                        reasons=result['reasons'],
                        filename=safe_filename
                    )
                    
                    display_video_results(result, safe_filename)
    
    st.markdown('</div>', unsafe_allow_html=True)

def display_video_results(result, filename):
    st.markdown('<h3 style="margin: 1.5rem 0;"> Analysis Results</h3>', unsafe_allow_html=True)
    
    # Main result card
    confidence_color = get_confidence_color(result['confidence_score'])
    status_emoji = "" if result['is_inappropriate'] else ""
    status_text = "Inappropriate" if result['is_inappropriate'] else "Appropriate"
    status_bg = "#f5f5f5" if result['is_inappropriate'] else "#f5f5f5"
    
    st.markdown(
        f'<div style="background: {status_bg}; padding: 2rem; border-radius: 4px; margin: 1rem 0; border-left: 5px solid {confidence_color};">'
        f'<div style="display: flex; justify-content: space-between; align-items: center;">'
        f'<h2 style="margin: 0; color: #111;">{status_emoji} {status_text}</h2>'
        f'<div style="text-align: right;">'
        f'<h3 style="margin: 0; color: {confidence_color};">Confidence: {result["confidence_score"]*100:.1f}%</h3>'
        f'</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.subheader(" Video Information")
        st.markdown(f"** Filename:** `{filename}`")
        
        if result['reasons']:
            st.subheader(" Detection Reasons")
            for reason in result['reasons']:
                st.markdown(f"• {reason}")
        else:
            st.markdown(" No specific issues detected")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        if result.get('details'):
            details = result['details']
            st.subheader(" Frame Analysis Summary")
            
            if details.get('analyzed_frames'):
                st.markdown(f"** Frames Analyzed:** {details['analyzed_frames']}")
            
            if details.get('inappropriate_frames'):
                st.markdown(f"** Flagged Frames:** {details['inappropriate_frames']}")
            
            if details.get('duration'):
                st.markdown(f"** Duration:** {details['duration']:.1f}s")
            
            if details.get('fps'):
                st.markdown(f"** Frame Rate:** {details['fps']:.1f} FPS")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Frame analysis details with enhanced styling
    if result.get('details') and result['details'].get('frame_analyses'):
        st.markdown('<h4 style="margin: 1.5rem 0 1rem 0;"> Detailed Frame Analysis</h4>', unsafe_allow_html=True)
        
        frame_analyses = result['details']['frame_analyses']
        flagged_frames = [f for f in frame_analyses if f['is_inappropriate']]
        
        if flagged_frames:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.subheader(f" Flagged Frames ({len(flagged_frames)} found)")
            
            for i, frame in enumerate(flagged_frames[:5]): # Show first 5 flagged frames
                confidence_color = get_confidence_color(frame['confidence_score'])
                st.markdown(
                    f'<div style="background: #f8f9fa; padding: 1rem; border-radius: 4px; margin: 0.5rem 0; border-left: 3px solid {confidence_color};">'
                    f'<strong> Frame at {frame["timestamp"]:.1f}s</strong><br>'
                    f'<span style="color: {confidence_color};">Confidence: {frame["confidence_score"]*100:.1f}%</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            
            if len(flagged_frames) > 5:
                st.info(f" And {len(flagged_frames) - 5} more flagged frames...")
            
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.success(" No inappropriate frames detected in the video!")

def show_content_review():
    st.markdown('<h2 class="section-header"> Content Review & Approval</h2>', unsafe_allow_html=True)
    
    # Get all analysis data
    all_data = st.session_state.data_manager.get_all_analysis()
    
    if all_data.empty:
        st.markdown(
            '<div style="background: #f5f5f5; padding: 2rem; border-radius: 4px; text-align: center; color: #111; margin: 2rem 0; border: 1px solid #e0e0e0;">'
            '<h3> No Content Available</h3>'
            '<p>No content is currently available for review. Content will appear here after analysis.</p>'
            '</div>',
            unsafe_allow_html=True
        )
        return
    
    # Modern filters with enhanced styling
    st.markdown('<h3 style="margin: 1.5rem 0 1rem 0;"> Filter Content</h3>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        status_filter = st.selectbox(
            " Status Filter", 
            ["All", "pending", "approved", "rejected"],
            help="Filter content by approval status"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        type_filter = st.selectbox(
            " Type Filter", 
            ["All"] + list(all_data['content_type'].unique()),
            help="Filter by content type"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        inappropriate_filter = st.selectbox(
            " Result Filter", 
            ["All", "Inappropriate", "Appropriate"],
            help="Filter by analysis result"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Apply filters
    filtered_data = all_data.copy()
    
    if status_filter != "All":
        filtered_data = filtered_data[filtered_data['status'] == status_filter]
    
    if type_filter != "All":
        filtered_data = filtered_data[filtered_data['content_type'] == type_filter]
    
    if inappropriate_filter == "Inappropriate":
        filtered_data = filtered_data[filtered_data['is_inappropriate'] == True]
    elif inappropriate_filter == "Appropriate":
        filtered_data = filtered_data[filtered_data['is_inappropriate'] == False]
    
    # Results summary
    st.markdown(
        f'<div style="background: #f5f5f5; padding: 1rem; border-radius: 4px; margin: 1rem 0; border: 1px solid #e0e0e0;">'
        f'<p style="margin: 0; text-align: center; font-weight: 600;"> Showing {len(filtered_data)} of {len(all_data)} items</p>'
        f'</div>',
        unsafe_allow_html=True
    )
    
    # Review items with modern cards
    if not filtered_data.empty:
        for idx, item in filtered_data.iterrows():
            confidence_color = get_confidence_color(item['confidence_score'])
            status_emoji = "" if item['is_inappropriate'] else ""
            
            with st.expander(
                f"{status_emoji} {item['content_type'].title()} - "
                f"{format_timestamp(item['timestamp'])} - "
                f"Status: {item['status'].title()}"
            ):
                # Create a modern review card
                st.markdown(
                    f'<div style="background: #ffffff; '
                    f'border-left: 5px solid {confidence_color}; padding: 1.5rem; border-radius: 4px; margin: 1rem 0;">',
                    unsafe_allow_html=True
                )
                
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    if item['content_type'] == 'text':
                        content_preview = str(item['content'])[:400] + "..." if len(str(item['content'])) > 400 else str(item['content'])
                        st.markdown("** Content Preview:**")
                        st.text_area("Content", content_preview, height=120, key=f"content_{idx}")
                    else:
                        st.markdown(f"** File:** `{item.get('filename', 'Unknown')}`")
                    
                    # Analysis details
                    result_emoji = "" if item['is_inappropriate'] else ""
                    st.markdown(f"**{result_emoji} Analysis Result:** {'Inappropriate' if item['is_inappropriate'] else 'Appropriate'}")
                    st.markdown(f"** Confidence:** {item['confidence_score']*100:.1f}%")
                    
                    if item['reasons']:
                        st.markdown("** Reasons:**")
                        for reason in item['reasons']:
                            st.markdown(f"• {reason}")
                    else:
                        st.markdown("**ℹ Reasons:** None specified")
                
                with col2:
                    st.markdown('<div style="text-align: center;">', unsafe_allow_html=True)
                    if st.button(" Approve", key=f"approve_{idx}", use_container_width=True):
                        st.session_state.data_manager.update_status(item['id'], 'approved')
                        st.success(" Content approved!")
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                
                with col3:
                    st.markdown('<div style="text-align: center;">', unsafe_allow_html=True)
                    if st.button(" Reject", key=f"reject_{idx}", use_container_width=True):
                        st.session_state.data_manager.update_status(item['id'], 'rejected')
                        st.error(" Content rejected!")
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)

def show_analytics():
    st.markdown('<h2 class="section-header"> Content Analytics</h2>', unsafe_allow_html=True)
    
    # Get analysis data
    all_data = st.session_state.data_manager.get_all_analysis()
    
    if all_data.empty:
        st.markdown(
            '<div style="background: #f5f5f5; padding: 2rem; border-radius: 4px; text-align: center; color: #111; margin: 2rem 0; border: 1px solid #e0e0e0;">'
            '<h3> No Analytics Data</h3>'
            '<p>No analysis data is available yet. Start analyzing content to see detailed analytics and insights.</p>'
            '</div>',
            unsafe_allow_html=True
        )
        return
    
    # Modern time range selector
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    time_range = st.selectbox(
        " Select Time Range", 
        ["Last 24 Hours", "Last 7 Days", "Last 30 Days", "All Time"],
        help="Choose the time period for analytics"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Filter data by time range
    now = datetime.now()
    if time_range == "Last 24 Hours":
        cutoff = now - timedelta(hours=24)
    elif time_range == "Last 7 Days":
        cutoff = now - timedelta(days=7)
    elif time_range == "Last 30 Days":
        cutoff = now - timedelta(days=30)
    else:
        cutoff = None
    
    if cutoff:
        filtered_data = all_data[pd.to_datetime(all_data['timestamp']) >= cutoff]
    else:
        filtered_data = all_data
    
    if filtered_data.empty:
        st.warning(f"No data available for {time_range.lower()}.")
        return
    
    # Enhanced key metrics with modern styling
    st.markdown('<h3 style="margin: 2rem 0 1rem 0;"> Key Performance Indicators</h3>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_analyzed = len(filtered_data)
        st.markdown(
            f'<div class="metric-container">'
            f'<h3 style="color: #4CAF50; margin: 0;"> {total_analyzed}</h3>'
            f'<p style="margin: 0; color: #666;">Total Analyzed</p>'
            f'</div>',
            unsafe_allow_html=True
        )
    
    with col2:
        inappropriate_count = len(filtered_data[filtered_data['is_inappropriate'] == True])
        inappropriate_rate = (inappropriate_count / total_analyzed * 100) if total_analyzed > 0 else 0
        rate_color = "#f44336" if inappropriate_rate > 10 else "#ff9800" if inappropriate_rate > 5 else "#4CAF50"
        st.markdown(
            f'<div class="metric-container">'
            f'<h3 style="color: {rate_color}; margin: 0;"> {inappropriate_count}</h3>'
            f'<p style="margin: 0; color: #666;">Inappropriate ({inappropriate_rate:.1f}%)</p>'
            f'</div>',
            unsafe_allow_html=True
        )
    
    with col3:
        avg_confidence = filtered_data['confidence_score'].mean()
        confidence_color = "#4CAF50" if avg_confidence < 0.5 else "#ff9800" if avg_confidence < 0.7 else "#f44336"
        st.markdown(
            f'<div class="metric-container">'
            f'<h3 style="color: {confidence_color}; margin: 0;"> {avg_confidence*100:.1f}%</h3>'
            f'<p style="margin: 0; color: #666;">Avg Confidence</p>'
            f'</div>',
            unsafe_allow_html=True
        )
    
    with col4:
        pending_count = len(filtered_data[filtered_data['status'] == 'pending'])
        pending_color = "#ff9800" if pending_count > 5 else "#4CAF50"
        st.markdown(
            f'<div class="metric-container">'
            f'<h3 style="color: {pending_color}; margin: 0;"> {pending_count}</h3>'
            f'<p style="margin: 0; color: #666;">Pending Review</p>'
            f'</div>',
            unsafe_allow_html=True
        )
    
    # Enhanced Charts with modern styling
    st.markdown('<h3 style="margin: 2rem 0 1rem 0;"> Visual Analytics</h3>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.subheader(" Content Type Distribution")
        type_counts = filtered_data['content_type'].value_counts()
        fig = px.pie(
            values=type_counts.values, 
            names=type_counts.index,
            color_discrete_sequence=['#4CAF50', '#111111', '#757575', '#388E3C', '#999999']
        )
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='#111111'
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.subheader(" Confidence Score Distribution")
        fig = px.histogram(
            filtered_data, 
            x='confidence_score', 
            nbins=20, 
            title="Confidence Score Distribution",
            color_discrete_sequence=['#4CAF50']
        )
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='#111111'
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Timeline analysis with modern styling
    if len(filtered_data) > 1:
        st.markdown('<h3 style="margin: 2rem 0 1rem 0;"> Timeline Analysis</h3>', unsafe_allow_html=True)
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.subheader(" Content Analysis Over Time")
        
        # Convert timestamp to datetime and create hourly aggregations
        filtered_data['datetime'] = pd.to_datetime(filtered_data['timestamp'])
        filtered_data['hour'] = filtered_data['datetime'].dt.floor('H')
        
        timeline_data = filtered_data.groupby(['hour', 'is_inappropriate']).size().reset_index(name='count')
        
        fig = px.line(
            timeline_data, 
            x='hour', 
            y='count', 
            color='is_inappropriate',
            title="Content Analysis Over Time",
            color_discrete_map={True: '#111111', False: '#4CAF50'}
        )
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='#111111'
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Top reasons for flagging with modern styling
    st.markdown('<h3 style="margin: 2rem 0 1rem 0;"> Flagging Analysis</h3>', unsafe_allow_html=True)
    
    inappropriate_data = filtered_data[filtered_data['is_inappropriate'] == True]
    if not inappropriate_data.empty:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.subheader(" Most Common Flagging Reasons")
        
        # Flatten reasons lists and count occurrences
        all_reasons = []
        for reasons_list in inappropriate_data['reasons']:
            if reasons_list:
                all_reasons.extend(reasons_list)
        
        if all_reasons:
            reason_counts = pd.Series(all_reasons).value_counts().head(10)
            fig = px.bar(
                x=reason_counts.values, 
                y=reason_counts.index, 
                orientation='h',
                title="Most Common Flagging Reasons",
                color_discrete_sequence=['#f44336']
            )
            fig.update_layout(
                yaxis={'categoryorder': 'total ascending'},
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='#111111'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(" No specific reasons recorded for flagged content.")
        
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="background: #f5f5f5; '
            'padding: 2rem; border-radius: 4px; text-align: center; color: #111; margin: 1rem 0;">'
            '<h4> Excellent!</h4>'
            '<p>No inappropriate content found in the selected time range. Your moderation is working effectively!</p>'
            '</div>',
            unsafe_allow_html=True
        )

if __name__ == "__main__":
    main()
