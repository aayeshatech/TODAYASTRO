import streamlit as st
import pandas as pd
from datetime import datetime
import re
import os
import requests
import time

# Telegram Configuration
BOT_TOKEN = '7613703350:AAGIvRqgsG_yTcOlFADRSYd_FtoLOPwXDKk'
CHAT_ID = '-1002840229810'

# Aspect interpretations
ASPECTS = {
    ('Mo','Ju'): "Bullish",
    ('Mo','Ve'): "Bullish",
    ('Mo','Sa'): "Bearish",
    ('Mo','Ra'): "Bearish",
    ('Mo','Ke'): "Bearish",
    ('Mo','Me'): "Neutral",
    ('Mo','Su'): "Neutral",
    ('Su','Ju'): "Strong Bullish",
    ('Su','Ve'): "Bullish",
    ('Su','Sa'): "Strong Bearish",
    ('Ma','Ju'): "Aggressive Bullish",
    ('Ma','Ve'): "Bullish",
    ('Ma','Sa'): "Bearish",
    ('Ju','Ve'): "Long Bullish",
    ('Sa','Ra'): "Strong Bearish",
    ('Ra','Ke'): "Extreme Bearish"
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

def generate_symbol_report(symbol, kp_data):
    """Generate report for specific symbol"""
    try:
        # Convert times to IST
        kp_data['Time_IST'] = kp_data['DateTime'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
        kp_data['Time_Str'] = kp_data['Time_IST'].dt.strftime('%I:%M %p')
        
        # Find all aspects for the symbol
        aspects = []
        for _, row in kp_data.iterrows():
            aspect_key = (row['Planet'], row['Sub_Lord'])
            if aspect_key in ASPECTS:
                aspects.append({
                    'Time': row['Time_Str'],
                    'Aspect': f"{row['Planet']}-{row['Sub_Lord']}",
                    'Sentiment': ASPECTS[aspect_key]
                })
        
        if not aspects:
            return None
        
        # Create report
        report = [
            f"🌟 {symbol.upper()} Astro Trading Report 🌟",
            f"📅 Date: {datetime.now().strftime('%d %b %Y')}",
            "",
            "🕒 Time    | 🔄 Aspect      | 📊 Sentiment",
            "―――――――――――――――――――――――――――――――――――――――"
        ]
        
        for aspect in aspects:
            report.append(f"{aspect['Time']} | {aspect['Aspect']:8} | {aspect['Sentiment']}")
        
        # Add summary
        bullish = [a for a in aspects if "Bullish" in a['Sentiment']]
        bearish = [a for a in aspects if "Bearish" in a['Sentiment']]
        
        report.extend([
            "",
            "📈 Bullish Aspects:",
            *[f"✅ {a['Time']} - {a['Aspect']}" for a in bullish[:3]],  # Top 3 bullish
            "",
            "📉 Bearish Aspects:",
            *[f"⚠️ {a['Time']} - {a['Aspect']}" for a in bearish[:3]],  # Top 3 bearish
            "",
            "⚠️ Note: Combine with technical analysis for best results"
        ])
        
        return "\n".join(report)
    
    except Exception as e:
        st.error(f"Report error: {str(e)}")
        return None

def send_to_telegram(message):
    """Send message to Telegram with retries"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    
    for _ in range(3):  # 3 retries
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                return True, "✅ Report sent to Telegram!"
            time.sleep(2)
        except Exception as e:
            time.sleep(2)
    
    return False, "❌ Failed to send to Telegram after 3 attempts"

def main():
    st.set_page_config(page_title="Astro Signal Finder", layout="centered")
    st.title("🔍 Astro Aspect Finder")
    
    # File upload
    uploaded_file = st.file_uploader("Upload kp_astro.txt", type="txt")
    if uploaded_file:
        try:
            with open("kp_astro.txt", "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success("File uploaded successfully!")
        except Exception as e:
            st.error(f"Error: {str(e)}")
            return
    
    if not os.path.exists("kp_astro.txt"):
        st.warning("Please upload kp_astro.txt file")
        return
    
    # Load data
    kp_data = parse_kp_astro("kp_astro.txt")
    if kp_data.empty:
        st.error("No valid data found in the file")
        return
    
    # Symbol input
    symbol = st.text_input("Enter Symbol (e.g., NIFTY, BANKNIFTY, GOLD)", "NIFTY").upper()
    
    if st.button("Generate & Send Report"):
        with st.spinner("Analyzing planetary aspects..."):
            report = generate_symbol_report(symbol, kp_data)
            
            if not report:
                st.error("No relevant aspects found for this symbol")
                return
            
            st.subheader("Generated Report")
            st.code(report)
            
            # Send to Telegram
            success, msg = send_to_telegram(report)
            if success:
                st.success(msg)
                st.balloons()
            else:
                st.error(msg)

if __name__ == "__main__":
    main()
