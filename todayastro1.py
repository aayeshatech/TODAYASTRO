import streamlit as st
import pandas as pd
from datetime import datetime
import re
import os
import requests
import pytz
import logging

# Telegram Configuration
BOT_TOKEN = '7613703350:AAGIvRqgsG_yTcOlFADRSYd_FtoLOPwXDKk'
CHAT_ID = '-1002840229810'

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='astro_trading.log'
)

# ========== Data Parser ==========
def parse_kp_astro(file_path):
    """Parse KP Astro data with robust error handling"""
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
                    dt = datetime.strptime(f"{parts[1]} {parts[2]}", '%Y-%m-%d %H:%M:%S')
                    data.append({
                        'Planet': parts[0],
                        'DateTime': dt,
                        'Motion': parts[3],
                        'Sign_Lord': parts[4],
                        'Star_Lord': parts[5],
                        'Sub_Lord': parts[6],
                        'Zodiac': parts[7],
                        'Nakshatra': parts[8],
                        'Pada': parts[9],
                        'Position': parts[10],
                        'Declination': parts[11] if len(parts) > 11 else ''
                    })
                except ValueError:
                    continue
        return pd.DataFrame(data)
    except Exception as e:
        logging.error(f"Parse error: {str(e)}")
        return pd.DataFrame()

# ========== Report Generator ==========
def generate_report(symbol, date, kp_data):
    """Generate formatted trading report"""
    try:
        # Convert times to IST
        kp_data['Time_IST'] = kp_data['DateTime'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata').dt.strftime('%I:%M %p')
        
        # Initialize report sections
        report = {
            'title': f"🚀 Aayeshatech Astro Trend | {symbol} Price Outlook ({date.strftime('%B %d, %Y')}) 🚀",
            'bullish': [],
            'bearish': [],
            'neutral': [],
            'strategy': []
        }
        
        # Aspect descriptions
        aspect_map = {
            ('Mo', 'Ju'): "Moon-Jupiter (Optimism in early trade)",
            ('Ve', 'Ma', 'Su'): "Venus-Mars-Sun (Short-term rally likely)",
            ('Mo', 'Ve'): "Moon-Venus (Recovery expected)",
            ('Ma', 'Ju'): "Mars-Jupiter (Strong bullish momentum)",
            ('Su', 'Sa', 'Ra'): "Sun-Saturn-Rahu (Early volatility)",
            ('Mo', 'Sa'): "Moon-Saturn (Downward pressure)",
            ('Mo', 'Ke'): "Moon-Ketu (Sharp drop possible)",
            ('Mo', 'Ma'): "Moon-Mars (Aggressive selling)",
            ('Mo', 'Ra'): "Moon-Rahu (Risk of panic selling)",
            ('Mo', 'Me'): "Moon-Mercury (Sideways movement)",
            ('Mo', 'Su'): "Moon-Sun (Mixed signals)"
        }
        
        # Analyze each entry
        for _, row in kp_data.iterrows():
            aspect_key = (row['Planet'], row['Sub_Lord'])
            aspect_key_3 = (row['Planet'], row['Star_Lord'], row['Sub_Lord'])
            
            if aspect_key_3 in aspect_map:
                desc = aspect_map[aspect_key_3]
            elif aspect_key in aspect_map:
                desc = aspect_map[aspect_key]
            else:
                continue
            
            # Categorize
            if row['Sub_Lord'] in ['Ju', 'Ve']:
                report['bullish'].append(f"✅ {row['Time_IST']} - {desc}")
            elif row['Sub_Lord'] in ['Sa', 'Ra', 'Ke', 'Ma']:
                report['bearish'].append(f"⚠️ {row['Time_IST']} - {desc}")
            else:
                report['neutral'].append(f"🔸 {row['Time_IST']} - {desc}")
        
        # Generate strategy
        if report['bullish']:
            best_times = ", ".join([x.split(' - ')[0] for x in report['bullish'][-2:]])
            report['strategy'].append(f"🔹 Buy Dips: Around {best_times}")
        if report['bearish']:
            sell_times = ", ".join([x.split(' - ')[0] for x in report['bearish'][-2:]])
            report['strategy'].append(f"🔹 Sell Rallies: After {sell_times}")
        
        # Format final message
        sections = [
            report['title'],
            "\n📈 Bullish Factors:",
            *report['bullish'],
            "\n📉 Bearish Factors:",
            *report['bearish'],
            "\n🔄 Neutral/Volatile:",
            *report['neutral'],
            "\n🎯 Trading Strategy:",
            *report['strategy'],
            "\nNote: Astro trends suggest volatility, trade with caution."
        ]
        
        return "\n".join(sections)
    
    except Exception as e:
        logging.error(f"Report error: {str(e)}")
        return None

# ========== Telegram Sender ==========
def send_to_telegram(message):
    """Send message with comprehensive error handling"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return True, "Message sent successfully!"
        
        error_info = response.json().get('description', 'Unknown error')
        return False, f"Telegram API Error: {error_info}"
        
    except Exception as e:
        return False, f"Connection Error: {str(e)}"

# ========== Streamlit UI ==========
def main():
    st.set_page_config(page_title="Aayeshatech Astro Alerts", layout="wide")
    st.title("📡 Astro Trading Telegram Alerts")
    
    # File upload
    uploaded_file = st.file_uploader("Upload kp astro.txt", type="txt")
    if uploaded_file:
        with open("kp astro.txt", "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success("File uploaded successfully!")
    
    if not os.path.exists("kp astro.txt"):
        st.warning("Please upload kp astro.txt file")
        return
    
    # Load data
    kp_df = parse_kp_astro("kp astro.txt")
    if kp_df.empty:
        st.error("No valid data found. Check file format.")
        return
    
    # User inputs
    col1, col2 = st.columns(2)
    with col1:
        selected_date = st.date_input(
            "Select date",
            value=kp_df['DateTime'].max().date(),
            min_value=kp_df['DateTime'].min().date(),
            max_value=kp_df['DateTime'].max().date()
        )
    with col2:
        symbol = st.text_input("Market Symbol", "GOLD").upper()
    
    # Generate and send report
    if st.button("Generate & Send Report"):
        filtered_data = kp_df[kp_df['DateTime'].dt.date == selected_date]
        
        if filtered_data.empty:
            st.error("No data for selected date")
            return
        
        with st.spinner("Generating report..."):
            report = generate_report(symbol, selected_date, filtered_data)
            
            if report:
                st.subheader("Report Preview")
                st.markdown(f"```\n{report}\n```")
                
                success, message = send_to_telegram(report)
                if success:
                    st.balloons()
                    st.success("✅ Report sent to Telegram!")
                else:
                    st.error(f"❌ {message}")
            else:
                st.error("Failed to generate report")

if __name__ == "__main__":
    main()
