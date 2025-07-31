import streamlit as st
import pandas as pd
import requests
import os
from datetime import datetime

# Configuration
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DATA_FILE = 'kp_astro.txt'

def get_api_key():
    """Get API key from multiple sources with priority order"""
    # 1. Check for direct input (takes precedence)
    if 'temp_api_key' in st.session_state and st.session_state.temp_api_key:
        return st.session_state.temp_api_key
    
    # 2. Check environment variables
    if 'DEEPSEEK_API_KEY' in os.environ:
        return os.environ['DEEPSEEK_API_KEY']
    
    # 3. Check Streamlit secrets
    try:
        return st.secrets["DEEPSEEK_API_KEY"]
    except (FileNotFoundError, KeyError, AttributeError):
        return None

@st.cache_data(ttl=3600)
def load_astro_data():
    """Load and preprocess astro data"""
    try:
        df = pd.read_csv(DATA_FILE, sep='\t')
        df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'])
        df['Date'] = df['DateTime'].dt.strftime('%Y-%m-%d')
        df['Time'] = df['DateTime'].dt.strftime('%H:%M:%S')
        return df.sort_values('DateTime')
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

def query_deepseek(prompt, astro_context=""):
    """Query DeepSeek API with enhanced error handling"""
    api_key = get_api_key()
    if not api_key:
        return "⚠️ Error: API key not configured. Please enter your API key below."
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    messages = [
        {
            "role": "system",
            "content": f"""You are an expert astrological AI analyst. Analyze this KP astro data:
            {astro_context}
            Provide detailed interpretations focusing on planetary influences.
            Use markdown formatting with bullet points for clear presentation.
            """
        },
        {"role": "user", "content": prompt}
    ]
    
    try:
        with st.spinner("🧠 Consulting DeepSeek AI..."):
            response = requests.post(
                DEEPSEEK_API_URL,
                headers=headers,
                json={
                    "model": "deepseek-chat",
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 1000
                },
                timeout=30
            )
        
        if response.status_code == 200:
            return response.json().get('choices', [{}])[0].get('message', {}).get('content', 'No response content')
        return f"🔴 API Error {response.status_code}: {response.text}"
    except Exception as e:
        return f"🔴 Connection Error: {str(e)}"

def main():
    st.set_page_config(
        page_title="KP Astro Analysis Engine",
        page_icon="🔮",
        layout="wide"
    )
    
    st.title("🔮 KP Astrological Analysis Engine")
    st.caption("Powered by DeepSeek AI")
    
    # API key configuration section
    if not get_api_key():
        st.warning("DeepSeek API key not configured", icon="⚠️")
        with st.expander("🔑 Enter API Key", expanded=True):
            st.session_state.temp_api_key = st.text_input(
                "Enter your DeepSeek API key:",
                type="password",
                help="Get your API key from DeepSeek's platform"
            )
            st.markdown("ℹ️ This key will only be stored for your current session")
    
    # Load and display data
    df = load_astro_data()
    if df.empty:
        st.error("No astro data loaded")
        return
    
    # Data filtering
    col1, col2 = st.columns(2)
    with col1:
        selected_planet = st.selectbox(
            "Select Planet",
            ["All"] + sorted(df['Planet'].unique()),
            index=0
        )
    with col2:
        selected_date = st.selectbox(
            "Select Date",
            ["All"] + sorted(df['Date'].unique()),
            index=0
        )
    
    filtered_df = df.copy()
    if selected_planet != "All":
        filtered_df = filtered_df[filtered_df['Planet'] == selected_planet]
    if selected_date != "All":
        filtered_df = filtered_df[filtered_df['Date'] == selected_date]
    
    # Display data
    st.subheader("📊 Planetary Positions")
    st.dataframe(
        filtered_df[['Planet', 'Date', 'Time', 'Motion', 'Sign Lord', 'Star Lord', 'Sub Lord']],
        use_container_width=True,
        hide_index=True,
        height=min(400, 35 * len(filtered_df) + 38)  # Dynamic height
    
    # AI Analysis
    st.divider()
    st.subheader("🤖 AI Astrological Analysis")
    
    query = st.text_area(
        "Enter your astrological query:",
        placeholder="E.g., What does Moon in Chitra mean for trading today?",
        height=120
    )
    
    if st.button("Analyze", type="primary", use_container_width=True):
        if not get_api_key():
            st.error("Please configure your API key first")
            return
        
        if not query.strip():
            st.warning("Please enter a query")
            return
        
        context = f"Current planetary positions:\n{filtered_df.to_string()}"
        analysis = query_deepseek(query, context)
        
        st.subheader("✨ Analysis Result")
        st.markdown("---")
        st.markdown(analysis)
        st.markdown("---")
        st.caption(f"Analysis generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
