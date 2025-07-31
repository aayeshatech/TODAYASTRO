import streamlit as st
import pandas as pd
from datetime import datetime
import re
import os
import requests
import json

# Telegram Configuration
BOT_TOKEN = '7613703350:AAGIvRqgsG_yTcOlFADRSYd_FtoLOPwXDKk'
CHAT_ID = '-1002840229810'

# Predefined symbol configurations
PREDEFINED_SYMBOLS = {
    'GOLD': {
        'bullish': [('Su','Ju'), ('Mo','Ju'), ('Ju','Ve')],
        'bearish': [('Sa','Ra'), ('Mo','Sa'), ('Mo','Ke')],
        'neutral': [('Mo','Me'), ('Mo','Su')],
        'strength': 1.2,
        'rulers': {'primary': 'Su', 'secondary': 'Ju', 'caution': 'Sa'}
    },
    'SILVER': {
        'bullish': [('Mo','Ve'), ('Ve','Ju'), ('Su','Ve')],
        'bearish': [('Sa','Ke'), ('Mo','Sa'), ('Ra','Ke')],
        'neutral': [('Mo','Me'), ('Su','Me')],
        'strength': 1.1,
        'rulers': {'primary': 'Mo', 'secondary': 'Ve', 'caution': 'Sa'}
    },
    'NIFTY': {
        'bullish': [('Ju','Me'), ('Mo','Ju'), ('Su','Ju')],
        'bearish': [('Sa','Ra'), ('Mo','Sa'), ('Ma','Sa')],
        'neutral': [('Mo','Me'), ('Ve','Me')],
        'strength': 1.0,
        'rulers': {'primary': 'Ju', 'secondary': 'Me', 'caution': 'Sa'}
    },
    'BANKNIFTY': {
        'bullish': [('Me','Ju'), ('Ma','Ju'), ('Su','Me')],
        'bearish': [('Sa','Ma'), ('Mo','Ra'), ('Sa','Ke')],
        'neutral': [('Mo','Ve'), ('Ju','Ve')],
        'strength': 1.3,
        'rulers': {'primary': 'Me', 'secondary': 'Ju', 'caution': 'Sa'}
    },
    'CRUDE': {
        'bullish': [('Ju','Ve'), ('Mo','Ju'), ('Su','Ve')],
        'bearish': [('Sa','Ke'), ('Mo','Sa'), ('Ra','Ke')],
        'neutral': [('Mo','Me'), ('Ve','Me')],
        'strength': 1.4,
        'rulers': {'primary': 'Ve', 'secondary': 'Ju', 'caution': 'Sa'}
    },
    'BTC': {
        'bullish': [('Ju','Me'), ('Mo','Ju'), ('Su','Ju')],
        'bearish': [('Sa','Ra'), ('Mo','Sa'), ('Ma','Sa')],
        'neutral': [('Mo','Me'), ('Ve','Me')],
        'strength': 1.5,
        'rulers': {'primary': 'Ju', 'secondary': 'Me', 'caution': 'Sa'}
    },
    'PHARMA': {
        'bullish': [('Ju','Ve'), ('Mo','Ju'), ('Su','Ve')],
        'bearish': [('Sa','Ke'), ('Mo','Sa'), ('Ra','Ke')],
        'neutral': [('Mo','Me'), ('Ve','Me')],
        'strength': 1.1,
        'rulers': {'primary': 'Ve', 'secondary': 'Ju', 'caution': 'Sa'}
    },
    'FMCG': {
        'bullish': [('Ju','Ve'), ('Mo','Ju'), ('Su','Ve')],
        'bearish': [('Sa','Ke'), ('Mo','Sa'), ('Ra','Ke')],
        'neutral': [('Mo','Me'), ('Ve','Me')],
        'strength': 1.0,
        'rulers': {'primary': 'Ve', 'secondary': 'Ju', 'caution': 'Sa'}
    },
    'AUTO': {
        'bullish': [('Ju','Me'), ('Mo','Ju'), ('Su','Ju')],
        'bearish': [('Sa','Ra'), ('Mo','Sa'), ('Ma','Sa')],
        'neutral': [('Mo','Me'), ('Ve','Me')],
        'strength': 1.2,
        'rulers': {'primary': 'Ju', 'secondary': 'Me', 'caution': 'Sa'}
    },
    'OIL AND GAS': {
        'bullish': [('Ju','Ve'), ('Mo','Ju'), ('Su','Ve')],
        'bearish': [('Sa','Ke'), ('Mo','Sa'), ('Ra','Ke')],
        'neutral': [('Mo','Me'), ('Ve','Me')],
        'strength': 1.3,
        'rulers': {'primary': 'Ve', 'secondary': 'Ju', 'caution': 'Sa'}
    },
    'DEFAULT': {
        'bullish': [('Mo','Ju'), ('Su','Ju'), ('Ju','Ve')],
        'bearish': [('Mo','Sa'), ('Sa','Ra'), ('Mo','Ke')],
        'neutral': [('Mo','Me'), ('Mo','Su')],
        'strength': 1.0,
        'rulers': {'primary': 'Ju', 'secondary': 'Su', 'caution': 'Sa'}
    }
}

def parse_kp_astro(file_path):
    """Parse KP Astro data file"""
    data = []
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('Planet'):
                    continue
                
                parts = re.split(r'\s+', line)
                if len(parts) < 11:
                    continue
                
                try:
                    dt_str = f"{parts[1]} {parts[2]}"
                    date_time = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
                    
                    data.append({
                        'Planet': parts[0],
                        'Date': parts[1],
                        'Time': parts[2],
                        'Motion': parts[3],
                        'Sign_Lord': parts[4],
                        'Star_Lord': parts[5],
                        'Sub_Lord': parts[6],
                        'Zodiac': parts[7],
                        'Nakshatra': parts[8],
                        'Pada': parts[9],
                        'Position': parts[10],
                        'Declination': parts[11] if len(parts) > 11 else '',
                        'DateTime': date_time
                    })
                except (ValueError, IndexError):
                    continue
        
        return pd.DataFrame(data)
    
    except Exception as e:
        st.error(f"Error parsing file: {str(e)}")
        return pd.DataFrame()

def get_symbol_config(symbol):
    """Get configuration for symbol (predefined or default)"""
    symbol = symbol.upper()
    return PREDEFINED_SYMBOLS.get(symbol, PREDEFINED_SYMBOLS['DEFAULT'])

def generate_symbol_report(symbol, kp_data):
    """Generate symbol-specific astro report"""
    try:
        symbol_config = get_symbol_config(symbol)
        
        # Convert times to IST
        kp_data['Time_IST'] = kp_data['DateTime'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
        kp_data['Time_Str'] = kp_data['Time_IST'].dt.strftime('%I:%M %p')
        
        # Find all relevant aspects for this symbol
        aspects = []
        for _, row in kp_data.iterrows():
            aspect = (row['Planet'], row['Sub_Lord'])
            
            if aspect in symbol_config['bullish']:
                aspects.append({
                    'Time': row['Time_Str'],
                    'Aspect': f"{row['Planet']}-{row['Sub_Lord']}",
                    'Sentiment': 'Bullish',
                    'Strength': symbol_config['strength']
                })
            elif aspect in symbol_config['bearish']:
                aspects.append({
                    'Time': row['Time_Str'],
                    'Aspect': f"{row['Planet']}-{row['Sub_Lord']}",
                    'Sentiment': 'Bearish',
                    'Strength': symbol_config['strength']
                })
            elif aspect in symbol_config['neutral']:
                aspects.append({
                    'Time': row['Time_Str'],
                    'Aspect': f"{row['Planet']}-{row['Sub_Lord']}",
                    'Sentiment': 'Neutral',
                    'Strength': symbol_config['strength']
                })
        
        if not aspects:
            return None
        
        # Create report
        report = [
            f"🌟 {symbol.upper()} Astro Trading Report 🌟",
            f"📅 Date: {datetime.now().strftime('%d %b %Y')}",
            f"📊 Symbol Strength: {symbol_config['strength']}x",
            "",
            "🕒 Time    | 🔄 Aspect      | 📊 Sentiment",
            "―――――――――――――――――――――――――――――――――――――――"
        ]
        
        # Add all aspects sorted by time
        for aspect in sorted(aspects, key=lambda x: x['Time']):
            emoji = "✅" if aspect['Sentiment'] == 'Bullish' else "⚠️" if aspect['Sentiment'] == 'Bearish' else "🔸"
            report.append(f"{aspect['Time']} | {aspect['Aspect']:8} | {emoji} {aspect['Sentiment']}")
        
        # Add trading recommendations
        bullish_times = [a['Time'] for a in aspects if a['Sentiment'] == 'Bullish']
        bearish_times = [a['Time'] for a in aspects if a['Sentiment'] == 'Bearish']
        
        report.extend([
            "",
            "📈 Best Buying Times:",
            *[f"✅ {time}" for time in bullish_times[:3]],
            "",
            "📉 Best Selling Times:",
            *[f"⚠️ {time}" for time in bearish_times[:3]],
            "",
            f"💡 {symbol.upper()} Planetary Rulers:",
            f"Primary: {symbol_config['rulers']['primary']} (Bullish)",
            f"Secondary: {symbol_config['rulers']['secondary']} (Neutral)",
            f"Caution: {symbol_config['rulers']['caution']} (Bearish)",
            "",
            "⚠️ Note: Timing based on planetary transits. Confirm with technicals."
        ])
        
        return "\n".join(report)
    
    except Exception as e:
        st.error(f"Report error: {str(e)}")
        return None

def send_to_telegram(message):
    """Send message to Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return True, "✅ Report sent to Telegram!"
        else:
            error_msg = f"❌ Telegram API Error: {response.status_code} - {response.text}"
            return False, error_msg
    except Exception as e:
        return False, f"❌ Connection error: {str(e)}"

def query_deepseek_ai(query_text):
    """
    Simulate DeepSeek AI query - Note: This is a placeholder
    Real implementation would require proper API access to DeepSeek
    """
    try:
        # This is a simulation - replace with actual DeepSeek API call
        simulated_response = f"""
🤖 DeepSeek AI Response:

Query: "{query_text}"

Analysis:
- Your query about "{query_text}" has been processed
- Based on current market conditions and astrological data
- Recommendation: Monitor planetary aspects for {query_text}
- Risk Level: Moderate
- Timing: Current planetary positions suggest caution

Note: This is a simulated response. For actual DeepSeek integration, 
you would need proper API credentials and endpoint access.

🔮 Astrological Insight:
The current planetary configuration suggests mixed signals for your query.
Venus and Jupiter aspects are favorable for financial decisions.
"""
        return True, simulated_response
    except Exception as e:
        return False, f"Error querying DeepSeek AI: {str(e)}"

def main():
    st.set_page_config(page_title="Enhanced Astro Symbol Tracker", layout="wide")
    
    # Header
    st.title("🌠 Enhanced Astro Symbol Tracker with AI Integration")
    st.markdown("---")
    
    # Sidebar for file upload and configuration
    with st.sidebar:
        st.header("📁 Configuration")
        uploaded_file = st.file_uploader("Upload kp_astro.txt", type="txt")
        if uploaded_file:
            try:
                with open("kp_astro.txt", "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.success("✅ KP Astro data loaded!")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                return
    
    # Create sample data if file doesn't exist
    if not os.path.exists("kp_astro.txt"):
        # Create sample data based on the provided data
        sample_data = """Planet	Date	Time	Motion	Sign Lord	Star Lord	Sub Lord	Zodiac	Nakshatra	Pada	Pos in Zodiac	Declination
Ve	2025-07-31	02:49:05	D	Me	Ma	Mo	Gemini	Mrigashira	4	05°33'20"	21.86
Mo	2025-07-31	03:16:01	D	Me	Ma	Ju	Virgo	Chitra	1	26°06'40"	-10.40
Mo	2025-07-31	06:50:00	D	Me	Ma	Sa	Virgo	Chitra	2	27°53'20"	-11.19
Mo	2025-07-31	11:04:33	D	Ve	Ma	Me	Libra	Chitra	3	00°00'00"	-12.13
Ju	2025-07-31	13:26:12	D	Me	Ra	Su	Gemini	Ardra	4	17°26'40"	22.85
Mo	2025-07-31	14:52:41	D	Ve	Ma	Ke	Libra	Chitra	3	01°53'20"	-12.95
Mo	2025-07-31	16:26:43	D	Ve	Ma	Ve	Libra	Chitra	3	02°40'00"	-13.29
Mo	2025-07-31	20:55:37	D	Ve	Ma	Su	Libra	Chitra	4	04°53'20"	-14.24
Mo	2025-07-31	22:16:21	D	Ve	Ma	Mo	Libra	Chitra	4	05°33'20"	-14.52"""
        
        with open("kp_astro.txt", "w") as f:
            f.write(sample_data)
        st.info("📝 Using sample KP Astro data")
    
    # Load data
    kp_data = parse_kp_astro("kp_astro.txt")
    if kp_data.empty:
        st.error("❌ No valid data found in file")
        return
    
    # Main content area with tabs
    tab1, tab2, tab3 = st.tabs(["📊 KP Astro Data", "🎯 Symbol Analysis", "🤖 AI Query"])
    
    with tab1:
        st.header("📊 KP Astro Data Table")
        
        # Display the data in table format
        display_df = kp_data.drop('DateTime', axis=1)  # Remove DateTime for cleaner display
        st.dataframe(
            display_df,
            use_container_width=True,
            height=400
        )
        
        # Quick stats
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Records", len(kp_data))
        with col2:
            st.metric("Unique Planets", kp_data['Planet'].nunique())
        with col3:
            st.metric("Unique Sub Lords", kp_data['Sub_Lord'].nunique())
        with col4:
            st.metric("Date Range", kp_data['Date'].iloc[0] if not kp_data.empty else "N/A")
    
    with tab2:
        st.header("🎯 Symbol Analysis")
        
        # Symbol selection
        col1, col2 = st.columns([3, 1])
        
        with col1:
            input_method = st.radio(
                "Select Symbol Input Method",
                options=["Choose from predefined", "Enter custom symbol"],
                horizontal=True
            )
            
            if input_method == "Choose from predefined":
                symbol = st.selectbox(
                    "Select Symbol",
                    options=['GOLD', 'SILVER', 'NIFTY', 'BANKNIFTY', 'CRUDE', 'BTC', 'PHARMA', 'FMCG', 'AUTO', 'OIL AND GAS'],
                    index=0
                )
            else:
                symbol = st.text_input(
                    "Enter Custom Symbol",
                    value="GOLD",
                    help="Enter any symbol name (will use default astro configuration)"
                ).upper()
        
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)  # Add some space
            search_button = st.button("🔍 Generate Report", type="primary", use_container_width=True)
        
        if search_button:
            with st.spinner(f"🔄 Analyzing {symbol} aspects..."):
                report = generate_symbol_report(symbol, kp_data)
                
                if not report:
                    st.error("❌ No relevant aspects found for selected date")
                else:
                    st.subheader(f"📈 {symbol} Astro Report")
                    st.code(report, language=None)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("📤 Send to Telegram"):
                            success, msg = send_to_telegram(report)
                            if success:
                                st.success(msg)
                                st.balloons()
                            else:
                                st.error(msg)
    
    with tab3:
        st.header("🤖 DeepSeek AI Query")
        st.markdown("Ask DeepSeek AI about market analysis, astrological insights, or trading strategies")
        
        # DeepSeek-style interface
        query_input = st.text_area(
            "Enter your query:",
            placeholder="Ask about market predictions, astrological analysis, or trading strategies...",
            height=100
        )
        
        col1, col2 = st.columns([1, 4])
        with col1:
            deepseek_button = st.button("🚀 Query DeepSeek", type="primary")
        
        if deepseek_button and query_input.strip():
            with st.spinner("🤖 Querying DeepSeek AI..."):
                success, response = query_deepseek_ai(query_input)
                
                if success:
                    st.subheader("🤖 DeepSeek AI Response")
                    st.markdown(response)
                    
                    # Option to send AI response to Telegram
                    if st.button("📤 Send AI Response to Telegram"):
                        telegram_success, telegram_msg = send_to_telegram(response)
                        if telegram_success:
                            st.success(telegram_msg)
                        else:
                            st.error(telegram_msg)
                else:
                    st.error(response)
        elif deepseek_button and not query_input.strip():
            st.warning("⚠️ Please enter a query before searching")
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: gray; font-size: 12px;'>
        Enhanced Astro Symbol Tracker v2.0 | Integrated with AI Analysis
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
