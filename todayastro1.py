import streamlit as st
import pandas as pd
import requests
import os
from datetime import datetime
import time

# Configuration
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"  # Example endpoint
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', st.secrets.get("DEEPSEEK_API_KEY", "your_api_key_here"))
DATA_FILE = 'kp_astro.txt'

def check_dependencies():
    """Check for required packages"""
    try:
        import pandas
        import requests
    except ImportError as e:
        st.error(f"Missing required dependency: {str(e)}. Please install with: pip install pandas requests")
        st.stop()

@st.cache_data(ttl=3600)
def load_astro_data():
    """Load and preprocess astro data with error handling"""
    try:
        df = pd.read_csv(DATA_FILE, sep='\t')
        
        # Convert to consistent datetime format
        df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'])
        df['Date'] = df['DateTime'].dt.strftime('%Y-%m-%d')
        df['Time'] = df['DateTime'].dt.strftime('%H:%M:%S')
        
        return df.sort_values('DateTime')
    except Exception as e:
        st.error(f"Error loading astro data: {str(e)}")
        return pd.DataFrame()

def query_deepseek(prompt, astro_context=""):
    """Query DeepSeek API with enhanced error handling"""
    if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY == "your_api_key_here":
        return "Error: DeepSeek API key not configured"
    
    headers = {
        'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    messages = [
        {
            "role": "system",
            "content": f"""You are an expert astrological AI analyst. Analyze this KP astro data:
            {astro_context}
            Provide detailed interpretations focusing on planetary influences, timing, and practical implications.
            Use markdown formatting for clear presentation.
            """
        },
        {"role": "user", "content": prompt}
    ]
    
    try:
        with st.spinner("Consulting DeepSeek AI..."):
            response = requests.post(
                DEEPSEEK_API_URL,
                headers=headers,
                json={
                    "model": "deepseek-chat",
                    "messages": messages,
                    "temperature": 0.7
                },
                timeout=15
            )
            
        if response.status_code == 200:
            return response.json().get('choices', [{}])[0].get('message', {}).get('content', 'No response content')
        else:
            return f"API Error (Status {response.status_code}): {response.text}"
            
    except requests.exceptions.RequestException as e:
        return f"Connection Error: {str(e)}"

def main():
    # Check dependencies first
    check_dependencies()
    
    st.set_page_config(
        page_title="KP Astro Analysis Engine",
        page_icon="🔮",
        layout="wide"
    )
    
    # Load data
    df = load_astro_data()
    
    # Sidebar filters
    with st.sidebar:
        st.header("🔍 Filters")
        selected_planet = st.selectbox(
            "Select Planet",
            ["All"] + sorted(df['Planet'].unique().tolist())
        )
        
        selected_date = st.selectbox(
            "Select Date",
            ["All"] + sorted(df['Date'].unique().tolist())
        )
    
    # Apply filters
    filtered_df = df.copy()
    if selected_planet != "All":
        filtered_df = filtered_df[filtered_df['Planet'] == selected_planet]
    if selected_date != "All":
        filtered_df = filtered_df[filtered_df['Date'] == selected_date]
    
    # Main display
    st.title("🔮 KP Astrological Analysis Engine")
    st.caption(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Data table - using Streamlit's native dataframe display
    st.dataframe(
        filtered_df[['Planet', 'Date', 'Time', 'Motion', 'Sign Lord', 'Star Lord', 'Sub Lord']],
        use_container_width=True,
        hide_index=True
    )
    
    # AI Analysis section
    st.divider()
    st.subheader("🤖 DeepSeek AI Analysis")
    
    query = st.text_area(
        "Ask about planetary influences:",
        placeholder="E.g., What does Moon in Chitra mean for trading today?"
    )
    
    if st.button("Get Analysis", type="primary") and query:
        # Convert DataFrame to string without tabulate
        context = filtered_df.to_string()
        analysis = query_deepseek(query, context)
        st.markdown("### AI Analysis Result")
        st.markdown(analysis)

if __name__ == "__main__":
    main()
