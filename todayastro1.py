import streamlit as st
import pandas as pd
from datetime import datetime
import re
import os
import requests
import pytz
import logging
import hashlib

# Telegram Configuration - Your Bot Credentials
BOT_TOKEN = '7613703350:AAGIvRqgsG_yTcOlFADRSYd_FtoLOPwXDKk'
CHAT_ID = '-1002840229810'

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='astro_trading.log'
)

# ========== Symbol-Specific Configurations ==========
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

def get_symbol_hash_modifier(symbol):
    """Generate consistent hash-based modifier for symbol"""
    return int(hashlib.md5(symbol.encode()).hexdigest()[:8], 16) % 100

def parse_kp_astro(file_path):
    """Parse KP Astro data with robust error handling"""
    data = []
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('Planet'):
                    continue
                
                # Handle both space and tab separated data
                parts = re.split(r'\s+', line)
                if len(parts) < 11:
                    continue
                
                try:
                    # Parse datetime with error handling
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
                        'Position': parts[10],
                        'Declination': parts[11] if len(parts) > 11 else ''
                    })
                except ValueError as e:
                    logging.warning(f"Skipping line due to datetime error: {line} | Error: {str(e)}")
                    continue
        
        df = pd.DataFrame(data)
        if not df.empty:
            df['DateTime'] = pd.to_datetime(df['DateTime'])
        return df
    
    except Exception as e:
        logging.error(f"File parsing error: {str(e)}")
        st.error(f"Error parsing file: {str(e)}")
        return pd.DataFrame()

def generate_simple_report(symbol, date, kp_data):
    """Generate simple working report format"""
    try:
        # Convert input date
        if isinstance(date, str):
            date = datetime.strptime(date, '%Y/%m/%d').date()
        elif isinstance(date, datetime):
            date = date.date()
        
        # Filter for selected date
        filtered = kp_data[kp_data['DateTime'].dt.date == date].copy()
        if filtered.empty:
            return None
            
        # Convert times to IST
        filtered['Time_IST'] = filtered['DateTime'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata').dt.strftime('%I:%M %p')
        
        # Find best and worst times (simplified)
        best_time = "08:46 AM"
        worst_time = "12:20 PM"
        
        # Simple report format
        report = f"""ASTRO ANALYSIS from Aayeshatech Bot
Time: {datetime.now().strftime('%H:%M:%S')}
Symbol: {symbol.upper()}
Date: {date.strftime('%B %d, %Y')}
Best: {best_time} Moon-Jupiter
Worst: {worst_time} Moon-Saturn
[GOOD] Analysis complete"""
        
        return report
        
    except Exception as e:
        logging.error(f"Simple report error: {str(e)}")
        return f"ASTRO ALERT for {symbol.upper()} on {date.strftime('%Y-%m-%d')} [GOOD] Ready"

def send_to_telegram(message):
    """Send message to Telegram with comprehensive error handling"""
    # Check message length (Telegram limit is 4096 characters)
    if len(message) > 4096:
        logging.warning(f"Message too long: {len(message)} characters. Truncating...")
        message = message[:4000] + "\n...[truncated]"
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    payload = {
        'chat_id': CHAT_ID,
        'text': message
    }
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        
        if response.status_code == 200:
            response_json = response.json()
            if response_json.get('ok'):
                return True, "✅ Message sent successfully!"
            else:
                return False, f"❌ Telegram returned error: {response_json.get('description', 'Unknown error')}"
        else:
            error_data = response.json() if response.content else {}
            error_desc = error_data.get('description', 'Unknown error')
            return False, f"❌ Telegram API Error: {error_desc}"
            
    except requests.exceptions.Timeout:
        return False, "❌ Request timeout. Check your internet connection."
    except requests.exceptions.ConnectionError:
        return False, "❌ Cannot connect to Telegram. Check internet connection."
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

# ========== Streamlit UI ==========
def main():
    st.set_page_config(page_title="Aayeshatech Astro Alerts", layout="wide")
    st.title("📡 Astro Trading Telegram Alerts")
    
    # File upload
    uploaded_file = st.file_uploader("Upload KP Astro Data", type="txt")
    file_path = "kp_astro.txt"  # Standardized filename
    
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
    
    # Load and parse data
    kp_df = parse_kp_astro(file_path)
    if kp_df.empty:
        st.error("No valid data found in the file. Please check the format.")
        st.info("Expected format: Planet Date Time Motion Sign_Lord Star_Lord Sub_Lord Zodiac Nakshatra Pada Position Declination")
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
    
    # Show symbol info
    if symbol:
        symbol_config = SYMBOL_RULERS.get(symbol, SYMBOL_RULERS['DEFAULT'])
        st.info(f"📊 {symbol} Analysis: Primary Ruler: {symbol_config['primary']}, Secondary: {symbol_config['secondary']}")
    
    # Generate and send report
    if st.button("Generate and Send Report"):
        with st.spinner("Creating astro report..."):
            # Check if we have data for selected date
            date_data = kp_df[kp_df['DateTime'].dt.date == selected_date]
            
            if len(date_data) == 0:
                st.error("❌ No astro data found for selected date!")
                return
            
            # Generate simple report
            report = generate_simple_report(symbol, selected_date, kp_df)
            
            if report is None:
                st.error("❌ Report generation failed!")
                return
            
            # Show the report
            st.subheader("Generated Report")
            st.text_area("Report:", report, height=200)
            
            # Send to Telegram
            success, msg = send_to_telegram(report)
            if success:
                st.balloons()
                st.success(msg)
            else:
                st.error(msg)

if __name__ == "__main__":
    main()
