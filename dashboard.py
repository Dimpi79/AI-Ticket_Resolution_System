import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import json
import os
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# Configuration
FLASK_API_URL = "http://localhost:5000"  # Your Flask app URL

st.set_page_config(
    page_title="AI Ticket System Analytics",
    page_icon="📊",
    layout="wide"
)

class FlaskTicketAnalytics:
    def __init__(self, base_url):
        self.base_url = base_url
        self.auth = ('admin', 'changeme')  # Use environment variables in production
    
    def get_feedback_data(self):
        """Fetch feedback data from Flask API"""
        try:
            response = requests.get(f"{self.base_url}/admin/feedback", auth=self.auth)
            if response.status_code == 200:
                return pd.DataFrame(response.json())
        except Exception as e:
            st.error(f"Error fetching feedback data: {e}")
        return pd.DataFrame()
    
    def get_content_gaps(self):
        """Fetch content gaps from Flask API"""
        try:
            response = requests.get(f"{self.base_url}/admin/api/gaps", auth=self.auth)
            if response.status_code == 200:
                return pd.DataFrame(response.json())
        except Exception as e:
            st.error(f"Error fetching content gaps: {e}")
        return pd.DataFrame()
    
    def get_knowledge_base(self):
        """Fetch KB articles from Flask API"""
        try:
            # You'll need to add this endpoint to your Flask app
            response = requests.get(f"{self.base_url}/admin/api/knowledge_base", auth=self.auth)
            if response.status_code == 200:
                return pd.DataFrame(response.json())
        except Exception as e:
            st.error(f"Error fetching KB data: {e}")
        return pd.DataFrame()

def main():
    st.title("🎫 AI Ticket System Analytics Dashboard")
    
    # Initialize analytics with Flask API
    analytics = FlaskTicketAnalytics(FLASK_API_URL)
    
    # Load data from Flask API
    with st.spinner('Loading data from ticket system...'):
        feedback_df = analytics.get_feedback_data()
        gaps_df = analytics.get_content_gaps()
        kb_df = analytics.get_knowledge_base()


st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

class TicketAnalytics:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.feedback_csv = os.path.join(data_dir, "feedback.csv")
        self.gaps_csv = os.path.join(data_dir, "content_gaps.csv")
        self.kb_csv = os.path.join(data_dir, "knowledge_base.csv")
        self.logs_jsonl = os.path.join(data_dir, "llm_logs.jsonl")
    
    def load_feedback_data(self):
        """Load and process feedback data"""
        if not os.path.exists(self.feedback_csv):
            return pd.DataFrame()
        
        df = pd.read_csv(self.feedback_csv)
        # Clean the data
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        return df
    
    def load_gaps_data(self):
        """Load content gaps data"""
        if not os.path.exists(self.gaps_csv):
            return pd.DataFrame()
        
        df = pd.read_csv(self.gaps_csv)
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        return df
    
    def load_kb_data(self):
        """Load knowledge base data"""
        if not os.path.exists(self.kb_csv):
            return pd.DataFrame()
        
        df = pd.read_csv(self.kb_csv)
        return df
    
    def load_logs_data(self):
        """Load LLM logs data"""
        if not os.path.exists(self.logs_jsonl):
            return pd.DataFrame()
        
        logs = []
        with open(self.logs_jsonl, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    logs.append(json.loads(line))
                except:
                    continue
        
        return pd.DataFrame(logs)

def create_category_chart(df):
    """Create bar chart for ticket categories"""
    if df.empty or 'final_category' not in df.columns:
        return None
    
    category_counts = df['final_category'].value_counts().reset_index()
    category_counts.columns = ['Category', 'Count']
    
    fig = px.bar(
        category_counts,
        x='Category',
        y='Count',
        title='📊 Tickets by Category',
        color='Count',
        color_continuous_scale='Blues'
    )
    fig.update_layout(
        xaxis_title="Category",
        yaxis_title="Number of Tickets",
        showlegend=False
    )
    return fig

def create_priority_chart(df):
    """Create pie chart for priority distribution"""
    if df.empty or 'final_priority' not in df.columns:
        return None
    
    priority_counts = df['final_priority'].value_counts().reset_index()
    priority_counts.columns = ['Priority', 'Count']
    
    # Define color mapping for priorities
    color_map = {
        'High': '#FF6B6B',
        'Medium': '#FFD166',
        'Low': '#06D6A0'
    }
    
    colors = [color_map.get(pri, '#999999') for pri in priority_counts['Priority']]
    
    fig = px.pie(
        priority_counts,
        values='Count',
        names='Priority',
        title='🎯 Priority Distribution',
        color_discrete_sequence=colors
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')
    return fig

def create_tags_wordcloud(df):
    """Create word cloud for most frequent tags"""
    if df.empty or 'final_tags' not in df.columns:
        return None
    
    # Combine all tags
    all_tags = ' '.join(df['final_tags'].dropna().astype(str))
    if not all_tags.strip():
        return None
    
    # Clean and process tags
    tags_clean = all_tags.replace(',', ' ').replace(';', ' ')
    
    # Create word cloud
    wordcloud = WordCloud(
        width=800,
        height=400,
        background_color='white',
        colormap='viridis',
        max_words=50
    ).generate(tags_clean)
    
    # Display using matplotlib
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis('off')
    ax.set_title('🏷️ Most Frequent Tags', fontsize=16, pad=20)
    
    return fig

def create_timeline_chart(df):
    """Create line chart for tickets over time"""
    if df.empty or 'timestamp' not in df.columns:
        return None
    
    # Group by date
    df['date'] = df['timestamp'].dt.date
    timeline_data = df.groupby('date').size().reset_index()
    timeline_data.columns = ['Date', 'Count']
    
    fig = px.line(
        timeline_data,
        x='Date',
        y='Count',
        title='📈 Tickets Over Time',
        markers=True
    )
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Number of Tickets"
    )
    return fig

def create_gaps_table(df):
    """Create table for content gaps"""
    if df.empty:
        return None
    
    # Select relevant columns and format
    display_cols = ['timestamp', 'ticket_excerpt']
    available_cols = [col for col in display_cols if col in df.columns]
    
    gaps_display = df[available_cols].copy()
    if 'timestamp' in gaps_display.columns:
        gaps_display['timestamp'] = gaps_display['timestamp'].dt.strftime('%Y-%m-%d %H:%M')
    
    return gaps_display

def main():
    # Header
    st.markdown('<h1 class="main-header">🎫 AI Ticket System Analytics Dashboard</h1>', unsafe_allow_html=True)
    
    # Initialize analytics
    analytics = TicketAnalytics()
    
    # Load data
    with st.spinner('Loading data...'):
        feedback_df = analytics.load_feedback_data()
        gaps_df = analytics.load_gaps_data()
        kb_df = analytics.load_kb_data()
    
    # Sidebar filters
    st.sidebar.title("🔧 Filters")
    
    # Date range filter
    if not feedback_df.empty and 'timestamp' in feedback_df.columns:
      start_default = feedback_df['timestamp'].min().date()
      end_default = datetime.today().date()

      date_range = st.sidebar.date_input(
        "Date Range",
        value=(start_default, end_default),
        min_value=start_default,
        max_value=end_default
      )

    if len(date_range) == 2:
        start_date, end_date = date_range
        feedback_df = feedback_df[
            (feedback_df['timestamp'].dt.date >= start_date) & 
            (feedback_df['timestamp'].dt.date <= end_date)
        ]

    
    # Key Metrics
    st.subheader("📈 Key Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_tickets = len(feedback_df) if not feedback_df.empty else 0
        st.metric("Total Tickets", total_tickets)
    
    with col2:
        content_gaps = len(gaps_df) if not gaps_df.empty else 0
        st.metric("Content Gaps", content_gaps)
    
    with col3:
        kb_articles = len(kb_df) if not kb_df.empty else 0
        st.metric("KB Articles", kb_articles)
    
    with col4:
        if not feedback_df.empty and 'final_priority' in feedback_df.columns:
            high_priority = len(feedback_df[feedback_df['final_priority'] == 'High'])
            st.metric("High Priority Tickets", high_priority)
        else:
            st.metric("High Priority Tickets", 0)
    
    # Charts Row 1
    col1, col2 = st.columns(2)
    
    with col1:
        category_chart = create_category_chart(feedback_df)
        if category_chart:
            st.plotly_chart(category_chart, use_container_width=True)
        else:
            st.info("No category data available")
    
    with col2:
        priority_chart = create_priority_chart(feedback_df)
        if priority_chart:
            st.plotly_chart(priority_chart, use_container_width=True)
        else:
            st.info("No priority data available")
    
    # Charts Row 2
    col1, col2 = st.columns(2)
    
    with col1:
        timeline_chart = create_timeline_chart(feedback_df)
        if timeline_chart:
            st.plotly_chart(timeline_chart, use_container_width=True)
        else:
            st.info("No timeline data available")
    
    with col2:
        tags_wordcloud = create_tags_wordcloud(feedback_df)
        if tags_wordcloud:
            st.pyplot(tags_wordcloud)
        else:
            st.info("No tags data available")
    
    # Content Gaps Table
    st.subheader("📋 Content Gaps (Missing KB Articles)")
    gaps_table = create_gaps_table(gaps_df)
    if gaps_table is not None and not gaps_table.empty:
        st.dataframe(
            gaps_table,
            use_container_width=True,
            hide_index=True
        )
        
        # Download button for gaps data
        csv_gaps = gaps_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Content Gaps Data",
            data=csv_gaps,
            file_name="content_gaps.csv",
            mime="text/csv"
        )
    else:
        st.info("No content gaps recorded yet")
    
    # Raw Data Section
    st.subheader("📁 Raw Data Preview")
    
    tab1, tab2, tab3 = st.tabs(["Feedback Data", "Content Gaps", "Knowledge Base"])
    
    with tab1:
        if not feedback_df.empty:
            st.dataframe(feedback_df, use_container_width=True)
            
            # Download button for feedback data
            csv_feedback = feedback_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Feedback Data",
                data=csv_feedback,
                file_name="feedback_data.csv",
                mime="text/csv"
            )
        else:
            st.info("No feedback data available")
    
    with tab2:
        if not gaps_df.empty:
            st.dataframe(gaps_df, use_container_width=True)
        else:
            st.info("No content gaps data available")
    
    with tab3:
        if not kb_df.empty:
            st.dataframe(kb_df, use_container_width=True)
            
            # Download button for KB data
            csv_kb = kb_df.to_csv(index=False)
            st.download_button(
                label="📥 Download KB Data",
                data=csv_kb,
                file_name="knowledge_base.csv",
                mime="text/csv"
            )
        else:
            st.info("No knowledge base data available")

if __name__ == "__main__":
    main()