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

# Initialize session state
if 'data_manager' not in st.session_state:
    st.session_state.data_manager = DataManager()
if 'text_analyzer' not in st.session_state:
    st.session_state.text_analyzer = TextAnalyzer()
if 'image_analyzer' not in st.session_state:
    st.session_state.image_analyzer = ImageAnalyzer()
if 'video_analyzer' not in st.session_state:
    st.session_state.video_analyzer = VideoAnalyzer()

def main():
    st.set_page_config(
        page_title="Content Moderation System",
        page_icon="🛡️",
        layout="wide"
    )
    
    st.title("🛡️ Content Moderation System")
    st.markdown("Real-time analysis and filtering of inappropriate content across text, images, and video")
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Select a page:",
        ["Dashboard", "Text Analysis", "Image Analysis", "Video Analysis", "Content Review", "Analytics"]
    )
    
    if page == "Dashboard":
        show_dashboard()
    elif page == "Text Analysis":
        show_text_analysis()
    elif page == "Image Analysis":
        show_image_analysis()
    elif page == "Video Analysis":
        show_video_analysis()
    elif page == "Content Review":
        show_content_review()
    elif page == "Analytics":
        show_analytics()

def show_dashboard():
    st.header("📊 Real-time Moderation Dashboard")
    
    # Get recent analysis data
    recent_data = st.session_state.data_manager.get_recent_analysis(hours=24)
    
    if recent_data.empty:
        st.info("No recent content analysis data available. Start analyzing content to see dashboard metrics.")
        return
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_items = len(recent_data)
        st.metric("Total Items (24h)", total_items)
    
    with col2:
        flagged_items = len(recent_data[recent_data['is_inappropriate'] == True])
        st.metric("Flagged Items", flagged_items, delta=f"{(flagged_items/total_items*100):.1f}% of total" if total_items > 0 else "0%")
    
    with col3:
        avg_confidence = recent_data['confidence_score'].mean()
        st.metric("Avg Confidence", f"{avg_confidence:.2f}" if not pd.isna(avg_confidence) else "N/A")
    
    with col4:
        pending_review = len(recent_data[recent_data['status'] == 'pending'])
        st.metric("Pending Review", pending_review)
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Content Analysis by Type")
        type_counts = recent_data['content_type'].value_counts()
        if not type_counts.empty:
            fig = px.pie(values=type_counts.values, names=type_counts.index, title="Content Type Distribution")
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Analysis Results")
        result_counts = recent_data['is_inappropriate'].value_counts()
        if not result_counts.empty:
            labels = ['Appropriate' if not x else 'Inappropriate' for x in result_counts.index]
            fig = px.bar(x=labels, y=result_counts.values, title="Content Appropriateness")
            st.plotly_chart(fig, use_container_width=True)
    
    # Recent flagged content
    st.subheader("🚨 Recent Flagged Content")
    flagged_data = recent_data[recent_data['is_inappropriate'] == True].head(10)
    
    if not flagged_data.empty:
        for _, item in flagged_data.iterrows():
            with st.expander(f"{item['content_type'].title()} - Confidence: {item['confidence_score']:.2f}"):
                col1, col2 = st.columns([3, 1])
                with col1:
                    if item['content_type'] == 'text':
                        st.text_area("Content", item['content'][:200] + "..." if len(str(item['content'])) > 200 else item['content'], height=100)
                    else:
                        st.write(f"**File:** {item.get('filename', 'Unknown')}")
                    st.write(f"**Reasons:** {', '.join(item['reasons']) if item['reasons'] else 'None specified'}")
                    st.write(f"**Timestamp:** {format_timestamp(item['timestamp'])}")
                with col2:
                    st.write(f"**Status:** {item['status'].title()}")
                    confidence_color = get_confidence_color(item['confidence_score'])
                    st.markdown(f"**Confidence:** <span style='color: {confidence_color}'>{item['confidence_score']:.2f}</span>", unsafe_allow_html=True)
    else:
        st.info("No flagged content in the last 24 hours.")

def show_text_analysis():
    st.header("📝 Text Content Analysis")
    
    # Input methods
    input_method = st.radio("Choose input method:", ["Type/Paste Text", "Upload File", "Batch Analysis"])
    
    if input_method == "Type/Paste Text":
        text_content = st.text_area("Enter text to analyze:", height=200, placeholder="Type or paste your content here...")
        
        if st.button("Analyze Text") and text_content:
            with st.spinner("Analyzing text content..."):
                result = st.session_state.text_analyzer.analyze(text_content)
                
                # Store result
                st.session_state.data_manager.store_analysis_result(
                    content_type='text',
                    content=text_content,
                    is_inappropriate=result['is_inappropriate'],
                    confidence_score=result['confidence_score'],
                    reasons=result['reasons']
                )
                
                # Display results
                display_text_results(result, text_content)
    
    elif input_method == "Upload File":
        uploaded_file = st.file_uploader("Choose a text file", type=['txt', 'md', 'csv'])
        
        if uploaded_file and st.button("Analyze File"):
            try:
                content = uploaded_file.read().decode('utf-8')
                with st.spinner("Analyzing file content..."):
                    result = st.session_state.text_analyzer.analyze(content)
                    
                    # Store result
                    st.session_state.data_manager.store_analysis_result(
                        content_type='text',
                        content=content,
                        is_inappropriate=result['is_inappropriate'],
                        confidence_score=result['confidence_score'],
                        reasons=result['reasons'],
                        filename=uploaded_file.name
                    )
                    
                    display_text_results(result, content, uploaded_file.name)
            except Exception as e:
                st.error(f"Error processing file: {str(e)}")
    
    elif input_method == "Batch Analysis":
        st.subheader("Batch Text Analysis")
        batch_text = st.text_area("Enter multiple texts (one per line):", height=300)
        
        if st.button("Analyze Batch") and batch_text:
            texts = [line.strip() for line in batch_text.split('\n') if line.strip()]
            
            if texts:
                progress_bar = st.progress(0)
                results = []
                
                for i, text in enumerate(texts):
                    result = st.session_state.text_analyzer.analyze(text)
                    results.append({
                        'text': text[:100] + '...' if len(text) > 100 else text,
                        'inappropriate': result['is_inappropriate'],
                        'confidence': result['confidence_score'],
                        'reasons': ', '.join(result['reasons'])
                    })
                    
                    # Store individual results
                    st.session_state.data_manager.store_analysis_result(
                        content_type='text',
                        content=text,
                        is_inappropriate=result['is_inappropriate'],
                        confidence_score=result['confidence_score'],
                        reasons=result['reasons']
                    )
                    
                    progress_bar.progress((i + 1) / len(texts))
                
                # Display batch results
                df = pd.DataFrame(results)
                st.subheader("Batch Analysis Results")
                st.dataframe(df, use_container_width=True)
                
                # Summary stats
                inappropriate_count = sum(1 for r in results if r['inappropriate'])
                st.metric("Flagged Items", f"{inappropriate_count}/{len(results)}")

def display_text_results(result, content, filename=None):
    st.subheader("Analysis Results")
    
    col1, col2 = st.columns(2)
    
    with col1:
        status = "🚨 Inappropriate" if result['is_inappropriate'] else "✅ Appropriate"
        st.write(f"**Status:** {status}")
        
        confidence_color = get_confidence_color(result['confidence_score'])
        st.markdown(f"**Confidence Score:** <span style='color: {confidence_color}'>{result['confidence_score']:.2f}</span>", unsafe_allow_html=True)
        
        if filename:
            st.write(f"**File:** {filename}")
    
    with col2:
        if result['reasons']:
            st.write("**Reasons:**")
            for reason in result['reasons']:
                st.write(f"• {reason}")
        else:
            st.write("**Reasons:** No specific issues detected")
    
    # Detailed analysis
    if result.get('details'):
        st.subheader("Detailed Analysis")
        details = result['details']
        
        if details.get('flagged_words'):
            st.write("**Flagged Words:**", ', '.join(details['flagged_words']))
        
        if details.get('sentiment'):
            sentiment = details['sentiment']
            st.write(f"**Sentiment:** {sentiment['label']} (Score: {sentiment['score']:.2f})")
        
        if details.get('toxicity_score'):
            st.write(f"**Toxicity Score:** {details['toxicity_score']:.2f}")

def show_image_analysis():
    st.header("🖼️ Image Content Analysis")
    
    uploaded_file = st.file_uploader("Choose an image file", type=['png', 'jpg', 'jpeg', 'gif', 'bmp'])
    
    if uploaded_file:
        # Display image
        st.image(uploaded_file, caption="Uploaded Image", use_column_width=True)
        
        if st.button("Analyze Image"):
            with st.spinner("Analyzing image content..."):
                # Convert to bytes for analysis
                image_bytes = uploaded_file.read()
                uploaded_file.seek(0)  # Reset file pointer
                
                result = st.session_state.image_analyzer.analyze(image_bytes)
                
                # Store result
                st.session_state.data_manager.store_analysis_result(
                    content_type='image',
                    content=f"Image file: {uploaded_file.name}",
                    is_inappropriate=result['is_inappropriate'],
                    confidence_score=result['confidence_score'],
                    reasons=result['reasons'],
                    filename=uploaded_file.name
                )
                
                # Display results
                st.subheader("Analysis Results")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    status = "🚨 Inappropriate" if result['is_inappropriate'] else "✅ Appropriate"
                    st.write(f"**Status:** {status}")
                    
                    confidence_color = get_confidence_color(result['confidence_score'])
                    st.markdown(f"**Confidence Score:** <span style='color: {confidence_color}'>{result['confidence_score']:.2f}</span>", unsafe_allow_html=True)
                
                with col2:
                    if result['reasons']:
                        st.write("**Reasons:**")
                        for reason in result['reasons']:
                            st.write(f"• {reason}")
                    else:
                        st.write("**Reasons:** No specific issues detected")
                
                # Additional details
                if result.get('details'):
                    details = result['details']
                    
                    st.subheader("Image Analysis Details")
                    
                    if details.get('detected_objects'):
                        st.write("**Detected Objects:**", ', '.join(details['detected_objects']))
                    
                    if details.get('color_analysis'):
                        st.write(f"**Dominant Colors:** {details['color_analysis']}")
                    
                    if details.get('face_count') is not None:
                        st.write(f"**Faces Detected:** {details['face_count']}")

def show_video_analysis():
    st.header("🎥 Video Content Analysis")
    
    uploaded_file = st.file_uploader("Choose a video file", type=['mp4', 'avi', 'mov', 'mkv'])
    
    if uploaded_file:
        st.video(uploaded_file)
        
        col1, col2 = st.columns(2)
        
        with col1:
            frame_interval = st.slider("Frame Analysis Interval (seconds)", 1, 10, 3)
        
        with col2:
            max_duration = st.slider("Max Analysis Duration (seconds)", 10, 300, 60)
        
        if st.button("Analyze Video"):
            with st.spinner("Analyzing video content... This may take a while."):
                # Save uploaded file temporarily
                video_bytes = uploaded_file.read()
                
                result = st.session_state.video_analyzer.analyze(
                    video_bytes, 
                    frame_interval=frame_interval,
                    max_duration=max_duration
                )
                
                # Store result
                st.session_state.data_manager.store_analysis_result(
                    content_type='video',
                    content=f"Video file: {uploaded_file.name}",
                    is_inappropriate=result['is_inappropriate'],
                    confidence_score=result['confidence_score'],
                    reasons=result['reasons'],
                    filename=uploaded_file.name
                )
                
                # Display results
                st.subheader("Analysis Results")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    status = "🚨 Inappropriate" if result['is_inappropriate'] else "✅ Appropriate"
                    st.write(f"**Status:** {status}")
                    
                    confidence_color = get_confidence_color(result['confidence_score'])
                    st.markdown(f"**Confidence Score:** <span style='color: {confidence_color}'>{result['confidence_score']:.2f}</span>", unsafe_allow_html=True)
                
                with col2:
                    if result['reasons']:
                        st.write("**Reasons:**")
                        for reason in result['reasons']:
                            st.write(f"• {reason}")
                    else:
                        st.write("**Reasons:** No specific issues detected")
                
                # Frame analysis details
                if result.get('details') and result['details'].get('frame_analyses'):
                    st.subheader("Frame Analysis Details")
                    
                    frame_analyses = result['details']['frame_analyses']
                    st.write(f"**Total Frames Analyzed:** {len(frame_analyses)}")
                    
                    flagged_frames = [f for f in frame_analyses if f['is_inappropriate']]
                    if flagged_frames:
                        st.write(f"**Flagged Frames:** {len(flagged_frames)}")
                        
                        for i, frame in enumerate(flagged_frames[:5]):  # Show first 5 flagged frames
                            st.write(f"Frame at {frame['timestamp']:.1f}s - Confidence: {frame['confidence_score']:.2f}")

def show_content_review():
    st.header("🔍 Content Review & Approval")
    
    # Get all analysis data
    all_data = st.session_state.data_manager.get_all_analysis()
    
    if all_data.empty:
        st.info("No content available for review.")
        return
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox("Filter by Status", ["All", "pending", "approved", "rejected"])
    
    with col2:
        type_filter = st.selectbox("Filter by Type", ["All"] + list(all_data['content_type'].unique()))
    
    with col3:
        inappropriate_filter = st.selectbox("Filter by Result", ["All", "Inappropriate", "Appropriate"])
    
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
    
    st.write(f"Showing {len(filtered_data)} of {len(all_data)} items")
    
    # Review items
    if not filtered_data.empty:
        for idx, item in filtered_data.iterrows():
            with st.expander(f"{item['content_type'].title()} - {format_timestamp(item['timestamp'])} - Status: {item['status'].title()}"):
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    if item['content_type'] == 'text':
                        content_preview = str(item['content'])[:300] + "..." if len(str(item['content'])) > 300 else str(item['content'])
                        st.text_area("Content", content_preview, height=100, key=f"content_{idx}")
                    else:
                        st.write(f"**File:** {item.get('filename', 'Unknown')}")
                    
                    st.write(f"**Analysis Result:** {'Inappropriate' if item['is_inappropriate'] else 'Appropriate'}")
                    st.write(f"**Confidence:** {item['confidence_score']:.2f}")
                    st.write(f"**Reasons:** {', '.join(item['reasons']) if item['reasons'] else 'None'}")
                
                with col2:
                    if st.button("Approve", key=f"approve_{idx}"):
                        st.session_state.data_manager.update_status(item['id'], 'approved')
                        st.success("Content approved!")
                        st.rerun()
                
                with col3:
                    if st.button("Reject", key=f"reject_{idx}"):
                        st.session_state.data_manager.update_status(item['id'], 'rejected')
                        st.error("Content rejected!")
                        st.rerun()

def show_analytics():
    st.header("📈 Content Analytics")
    
    # Get analysis data
    all_data = st.session_state.data_manager.get_all_analysis()
    
    if all_data.empty:
        st.info("No data available for analytics.")
        return
    
    # Time range selector
    time_range = st.selectbox("Select Time Range", ["Last 24 Hours", "Last 7 Days", "Last 30 Days", "All Time"])
    
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
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_analyzed = len(filtered_data)
        st.metric("Total Analyzed", total_analyzed)
    
    with col2:
        inappropriate_count = len(filtered_data[filtered_data['is_inappropriate'] == True])
        inappropriate_rate = (inappropriate_count / total_analyzed * 100) if total_analyzed > 0 else 0
        st.metric("Inappropriate Content", f"{inappropriate_count}", f"{inappropriate_rate:.1f}%")
    
    with col3:
        avg_confidence = filtered_data['confidence_score'].mean()
        st.metric("Avg Confidence", f"{avg_confidence:.2f}")
    
    with col4:
        pending_count = len(filtered_data[filtered_data['status'] == 'pending'])
        st.metric("Pending Review", pending_count)
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Content Type Distribution")
        type_counts = filtered_data['content_type'].value_counts()
        fig = px.pie(values=type_counts.values, names=type_counts.index)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Confidence Score Distribution")
        fig = px.histogram(filtered_data, x='confidence_score', nbins=20, title="Confidence Score Distribution")
        st.plotly_chart(fig, use_container_width=True)
    
    # Timeline analysis
    if len(filtered_data) > 1:
        st.subheader("Analysis Timeline")
        
        # Convert timestamp to datetime and create hourly aggregations
        filtered_data['datetime'] = pd.to_datetime(filtered_data['timestamp'])
        filtered_data['hour'] = filtered_data['datetime'].dt.floor('H')
        
        timeline_data = filtered_data.groupby(['hour', 'is_inappropriate']).size().reset_index(name='count')
        
        fig = px.line(timeline_data, x='hour', y='count', color='is_inappropriate', 
                     title="Content Analysis Over Time")
        st.plotly_chart(fig, use_container_width=True)
    
    # Top reasons for flagging
    st.subheader("Top Reasons for Flagging")
    
    inappropriate_data = filtered_data[filtered_data['is_inappropriate'] == True]
    if not inappropriate_data.empty:
        # Flatten reasons lists and count occurrences
        all_reasons = []
        for reasons_list in inappropriate_data['reasons']:
            if reasons_list:
                all_reasons.extend(reasons_list)
        
        if all_reasons:
            reason_counts = pd.Series(all_reasons).value_counts().head(10)
            fig = px.bar(x=reason_counts.values, y=reason_counts.index, orientation='h',
                        title="Most Common Flagging Reasons")
            fig.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No specific reasons recorded for flagged content.")
    else:
        st.info("No inappropriate content found in the selected time range.")

if __name__ == "__main__":
    main()
