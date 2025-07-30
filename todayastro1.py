import streamlit as st
import pandas as pd
from datetime import datetime
import re
import os
import requests

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
                        'DateTime': date_time,
                        'Sub_Lord': parts[6]
                    })
                except ValueError:
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
        return response.status_code == 200, "✅ Report sent to Telegram!" if response.status_code == 200 else "❌ Failed to send"
    except Exception:
        return False, "❌ Connection error"

def main():
    st.set_page_config(page_title="Astro Symbol Tracker", layout="centered")
    st.title("🌠 Symbol-Specific Astro Report")
    
    # File upload
    uploaded_file = st.file_uploader("Upload kp_astro.txt", type="txt")
    if uploaded_file:
        try:
            with open("kp_astro.txt", "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success("KP Astro data loaded!")
        except Exception as e:
            st.error(f"Error: {str(e)}")
            return
    
    if not os.path.exists("kp_astro.txt"):
        st.warning("Please upload kp_astro.txt file")
        return
    
    # Load data
    kp_data = parse_kp_astro("kp_astro.txt")
    if kp_data.empty:
        st.error("No valid data found in file")
        return
    
    # Symbol input
    input_method = st.radio(
        "Select Symbol Input Method",
        options=["Choose from predefined", "Enter custom symbol"],
        horizontal=True
    )
    
    if input_method == "Choose from predefined":
        symbol = st.selectbox(
            "Select Symbol",
            options=list(PREDEFINED_SYMBOLS.keys())[:-1],  # Exclude DEFAULT
            index=0
        )
    else:
        symbol = st.text_input(
            "Enter Custom Symbol",
            value="GOLD",
            help="Enter any symbol name (will use default astro configuration)"
        ).upper()
    
    if st.button("Generate Symbol Report"):
        with st.spinner(f"Analyzing {symbol} aspects..."):
            report = generate_symbol_report(symbol, kp_data)
            
            if not report:
                st.error("No relevant aspects found for selected date")
                return
            
            st.subheader(f"{symbol} Astro Report")
            st.code(report)
            
            if st.button("📤 Send to Telegram"):
                success, msg = send_to_telegram(report)
                if success:
                    st.success(msg)
                    st.balloons()
                else:
                    st.error(msg)

if __name__ == "__main__":
    main()
