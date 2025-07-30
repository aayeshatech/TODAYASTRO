import streamlit as st
import pandas as pd
from datetime import datetime
import re
import os
import requests
import pytz
import logging
import hashlib

# Telegram Configuration
BOT_TOKEN = '7613703350:AAGIvRqgsG_yTcOlFADRSYd_FtoLOPwXDKk'
CHAT_ID = '-1002840229810'

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='astro_trading.log'
)

# Symbol Configurations
SYMBOL_RULERS = {
    'GOLD': {'primary': 'Su', 'secondary': 'Ju', 'bearish': ['Sa', 'Ra'], 'strength': 1.2},
    'SILVER': {'primary': 'Mo', 'secondary': 'Ve', 'bearish': ['Sa', 'Ke'], 'strength': 1.1},
    'CRUDE': {'primary': 'Ma', 'secondary': 'Sa', 'bearish': ['Ra', 'Ke'], 'strength': 1.3},
    'NIFTY': {'primary': 'Ju', 'secondary': 'Me', 'bearish': ['Sa', 'Ra'], 'strength': 1.0},
    'BANKNIFTY': {'primary': 'Me', 'secondary': 'Ju', 'bearish': ['Sa', 'Ma'], 'strength': 1.1},
    'SENSEX': {'primary': 'Ju', 'secondary': 'Su', 'bearish': ['Sa', 'Ra'], 'strength': 1.0},
    'USDINR': {'primary': 'Me', 'secondary': 'Ra', 'bearish': ['Sa', 'Ke'], 'strength': 0.9},
    'BTCUSD': {'primary': 'Ra', 'secondary': 'Me', 'bearish': ['Sa', 'Ke'], 'strength': 1.5},
    'ETHUSDT': {'primary': 'Ra', 'secondary': 'Ve', 'bearish': ['Sa', 'Ma'], 'strength': 1.4},
    'DEFAULT': {'primary': 'Su', 'secondary': 'Ju', 'bearish': ['Sa', 'Ra'], 'strength': 1.0}
}

# Aspect interpretations
ASPECTS = {
    ('Mo','Ju'): "Optimism in early trade",
    ('Mo','Ve'): "Recovery expected",
    ('Mo','Sa'): "Downward pressure",
    ('Mo','Ra'): "Risk of panic selling",
    ('Mo','Ke'): "Sharp drop possible",
    ('Mo','Me'): "Sideways movement",
    ('Mo','Su'): "Mixed signals",
    ('Su','Ju'): "Strong bullish momentum",
    ('Su','Ve'): "Positive sentiment",
    ('Su','Sa'): "Institutional selling",
    ('Ma','Ju'): "Aggressive buying",
    ('Ma','Ve'): "Speculative rally",
    ('Ma','Sa'): "Correction likely",
    ('Ju','Ve'): "Sustained uptrend",
    ('Sa','Ra'): "Major decline risk",
    ('Ra','Ke'): "Extreme volatility"
}

def parse_kp_astro(file_path):
    """Parse KP Astro data"""
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
                        'Sign_Lord': parts[4],
                        'Star_Lord': parts[5],
                        'Sub_Lord': parts[6],
                        'Zodiac': parts[7],
                        'Nakshatra': parts[8],
                        'Pada': parts[9],
                        'Position': parts[10]
                    })
                except ValueError:
                    continue
        
        df = pd.DataFrame(data)
        if not df.empty:
            df['DateTime'] = pd.to_datetime(df['DateTime'])
        return df
    
    except Exception as e:
        st.error(f"Error parsing file: {str(e)}")
        return pd.DataFrame()

def generate_formatted_report(symbol, date, kp_data):
    """Generate report in the exact specified format"""
    try:
        # Filter for selected date
        filtered = kp_data[kp_data['DateTime'].dt.date == date].copy()
        if filtered.empty:
            return None
            
        # Convert times to IST
        filtered['Time_IST'] = filtered['DateTime'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata').dt.strftime('%I:%M %p')
        
        # Categorize aspects
        bullish = []
        bearish = []
        neutral = []
        
        for _, row in filtered.iterrows():
            aspect_key = (row['Planet'], row['Sub_Lord'])
            desc = ASPECTS.get(aspect_key, "Market movement expected")
            
            if aspect_key in [('Mo','Ju'), ('Mo','Ve'), ('Su','Ju'), ('Su','Ve'), ('Ma','Ju'), ('Ma','Ve'), ('Ju','Ve')]:
                bullish.append(f"✅ {row['Time_IST']} - {row['Planet']}-{row['Sub_Lord']} ({desc})")
            elif aspect_key in [('Mo','Sa'), ('Mo','Ra'), ('Mo','Ke'), ('Su','Sa'), ('Ma','Sa'), ('Sa','Ra'), ('Ra','Ke')]:
                bearish.append(f"⚠️ {row['Time_IST']} - {row['Planet']}-{row['Sub_Lord']} ({desc})")
            else:
                neutral.append(f"🔸 {row['Time_IST']} - {row['Planet']}-{row['Sub_Lord']} ({desc})")
        
        # Sort by time
        for category in [bullish, bearish, neutral]:
            category.sort(key=lambda x: datetime.strptime(x.split(' - ')[0][2:].strip(), '%I:%M %p'))
        
        # Generate strategy
        strategy = []
        if bullish:
            best_times = [x.split(' - ')[0] for x in bullish[:2]]
            strategy.append(f"🔹 Buy Dips: Around {', '.join(best_times)}")
        if bearish:
            sell_times = [x.split(' - ')[0] for x in bearish[:2]]
            strategy.append(f"🔹 Sell Rallies: After {', '.join(sell_times)}")
        
        # Build report in exact format
        report = [
            f"🚀 Aayeshatech Astro Trend | {symbol.upper()} Price Outlook ({date.strftime('%B %d, %Y')}) 🚀",
            "",
            "📈 Bullish Factors:"
        ]
        report.extend(bullish[:3])  # Show top 3 bullish
        
        report.extend([
            "",
            "📉 Bearish Factors:"
        ])
        report.extend(bearish[:3])  # Show top 3 bearish
        
        report.extend([
            "",
            "🔄 Neutral/Volatile:"
        ])
        report.extend(neutral[:2])  # Show top 2 neutral
        
        report.extend([
            "",
            "🎯 Trading Strategy:"
        ])
        report.extend(strategy)
        
        report.extend([
            "",
            "⚠️ Note: Astro trends suggest volatility, trade with caution."
        ])
        
        return "\n".join(report)
    
    except Exception as e:
        logging.error(f"Report generation error: {str(e)}")
        return None

def send_to_telegram(message):
    """Send message to Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message
    }
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            return True, "✅ Message sent successfully!"
        else:
            return False, f"❌ Telegram API Error"
    except Exception:
        return False, "❌ Failed to connect to Telegram"

def main():
    st.set_page_config(page_title="Aayeshatech Astro Alerts", layout="wide")
    st.title("📡 Astro Trading Telegram Alerts")
    
    # File upload
    uploaded_file = st.file_uploader("Upload KP Astro Data", type="txt")
    file_path = "kp_astro.txt"
    
    if uploaded_file is not None:
        try:
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success("File uploaded successfully!")
        except Exception as e:
            st.error(f"Error saving file: {str(e)}")
            return
    
    if not os.path.exists(file_path):
        st.warning("Please upload KP Astro data file")
        return
    
    # Load data
    kp_df = parse_kp_astro(file_path)
    if kp_df.empty:
        st.error("No valid data found in the file.")
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
        symbol = st.text_input("Market Symbol", "NIFTY").upper()
    
    # Generate and send report
    if st.button("Generate and Send Report"):
        with st.spinner("Creating astro report..."):
            report = generate_formatted_report(symbol, selected_date, kp_df)
            
            if report is None:
                st.error("Failed to generate report")
                return
            
            st.subheader("Generated Report")
            st.text_area("Report:", report, height=300)
            
            success, msg = send_to_telegram(report)
            if success:
                st.balloons()
                st.success(msg)
            else:
                st.error(msg)

if __name__ == "__main__":
    main()
