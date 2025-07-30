import streamlit as st
import pandas as pd
from datetime import datetime
import re
import os
import requests
import pytz
import logging

# ========== Telegram Configuration ==========
BOT_TOKEN = '7613703350:AAGIvRqgsG_yTcOlFADRSYd_FtoLOPwXDKk'
CHAT_ID = '-1002840229810'

# ========== Setup Logging ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='astro_trading.log'
)

# ========== Enhanced Telegram Sender ==========
def send_to_telegram(message):
    """Send message to Telegram with comprehensive error handling"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown',
        'disable_web_page_preview': True
    }
    
    try:
        response = requests.post(
            url,
            json=payload,
            timeout=10
        )
        
        logging.info(f"Telegram API Response: {response.status_code} - {response.text}")
        
        if response.status_code == 200:
            return True, "Message sent successfully!"
        
        # Handle specific Telegram API errors
        error_info = response.json().get('description', 'Unknown error')
        if "chat not found" in error_info.lower():
            return False, "Error: Chat ID not found. Please verify CHAT_ID."
        elif "bot token" in error_info.lower():
            return False, "Error: Invalid bot token. Please verify BOT_TOKEN."
        else:
            return False, f"Telegram API Error: {error_info}"
            
    except requests.exceptions.Timeout:
        logging.error("Telegram API timeout")
        return False, "Error: Request timeout. Check your internet connection."
    except requests.exceptions.RequestException as e:
        logging.error(f"Telegram connection error: {str(e)}")
        return False, f"Connection Error: {str(e)}"
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return False, f"Unexpected Error: {str(e)}"

# ========== Report Generator ==========
def generate_report(symbol, date, kp_data):
    """Generate formatted trading report"""
    try:
        date_str = date.strftime('%B %d, %Y')
        report = [f"🚀 Aayeshatech Astro Trend | {symbol} Price Outlook ({date_str}) 🚀\n"]
        
        # Convert times to IST
        kp_data['Time_IST'] = kp_data['DateTime'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata').dt.strftime('%I:%M %p')
        
        # ===== Bullish Factors =====
        bullish = kp_data[
            (kp_data['Sub_Lord'].isin(['Ju', 'Ve'])) &
            (kp_data['Planet'].isin(['Mo', 'Su']))
        ].sort_values('DateTime')
        
        if not bullish.empty:
            report.append("\n📈 Bullish Factors:")
            for _, row in bullish.iterrows():
                desc = get_aspect_description(row)
                report.append(f"✅ {row['Time_IST']} - {desc}")
        
        # ===== Bearish Factors =====
        bearish = kp_data[
            (kp_data['Sub_Lord'].isin(['Sa', 'Ra', 'Ke', 'Ma'])) &
            (kp_data['Planet'].isin(['Mo', 'Su']))
        ].sort_values('DateTime')
        
        if not bearish.empty:
            report.append("\n📉 Bearish Factors:")
            for _, row in bearish.iterrows():
                desc = get_aspect_description(row)
                report.append(f"⚠️ {row['Time_IST']} - {desc}")
        
        # ===== Trading Strategy =====
        report.append("\n🎯 Trading Strategy:")
        
        if not bullish.empty:
            best_times = ", ".join(bullish['Time_IST'].head(2).tolist())
            report.append(f"🔹 Buy Dips: Around {best_times}")
        
        if not bearish.empty:
            sell_times = ", ".join(bearish['Time_IST'].head(2).tolist())
            report.append(f"🔹 Sell Rallies: After {sell_times}")
        
        report.append("\nNote: Astro trends suggest volatility, trade with caution.")
        
        return "\n".join(report)
    
    except Exception as e:
        logging.error(f"Report generation error: {str(e)}")
        return None

def get_aspect_description(row):
    """Generate human-readable aspect descriptions"""
    planet_map = {
        'Mo': 'Moon', 'Su': 'Sun', 'Me': 'Mercury',
        'Ve': 'Venus', 'Ma': 'Mars', 'Ju': 'Jupiter',
        'Sa': 'Saturn', 'Ra': 'Rahu', 'Ke': 'Ketu'
    }
    
    descriptions = {
        ('Mo', 'Ju'): "Moon-Jupiter (Optimism in early trade)",
        ('Mo', 'Ve'): "Moon-Venus (Recovery expected)",
        ('Su', 'Ju'): "Sun-Jupiter (Strong bullish momentum)",
        ('Mo', 'Sa'): "Moon-Saturn (Downward pressure)",
        ('Mo', 'Ra'): "Moon-Rahu (Risk of panic selling)",
        ('Mo', 'Ma'): "Moon-Mars (Aggressive selling)",
        ('Mo', 'Ke'): "Moon-Ketu (Sharp drop possible)",
        ('Su', 'Sa'): "Sun-Saturn-Rahu (Early volatility)",
        ('Su', 'Ma'): "Sun-Mars (Short-term rally likely)"
    }
    
    default = f"{planet_map.get(row['Planet'], row['Planet'])}-{planet_map.get(row['Sub_Lord'], row['Sub_Lord'])}"
    
    return descriptions.get(
        (row['Planet'], row['Sub_Lord']),
        f"{default} (Watch for movement)"
    )

# ========== Streamlit UI ==========
def main():
    st.set_page_config(page_title="Aayeshatech Astro Alerts", layout="wide")
    st.title("📡 Astro Trading Telegram Alerts")
    
    # Debugging panel
    with st.expander("🔧 Debug Settings", expanded=False):
        st.code(f"BOT_TOKEN: {'*'*len(BOT_TOKEN) if BOT_TOKEN else 'NOT SET'}")
        st.code(f"CHAT_ID: {CHAT_ID}")
        if st.button("Test Telegram Connection"):
            test_result = send_to_telegram("🔔 Aayeshatech Bot Connection Test")
            if test_result[0]:
                st.success("✅ Test message sent successfully!")
            else:
                st.error(f"❌ {test_result[1]}")
    
    # File upload
    uploaded_file = st.file_uploader("Upload kp astro.txt", type="txt")
    if uploaded_file:
        with open("kp astro.txt", "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success("File uploaded successfully!")
    
    if not os.path.exists("kp astro.txt"):
        st.warning("Please upload kp astro.txt file")
        return
    
    # Load and parse data
    try:
        kp_data = pd.read_csv("kp astro.txt", sep='\s+', header=None,
                            names=['Planet', 'Date', 'Time', 'Motion', 'Sign_Lord', 
                                  'Star_Lord', 'Sub_Lord', 'Zodiac', 'Nakshatra', 
                                  'Pada', 'Position', 'Declination'])
        kp_data['DateTime'] = pd.to_datetime(kp_data['Date'] + ' ' + kp_data['Time'])
    except Exception as e:
        st.error(f"Error parsing file: {str(e)}")
        return
    
    # Report parameters
    col1, col2 = st.columns(2)
    with col1:
        selected_date = st.date_input(
            "Select date",
            value=kp_data['DateTime'].max().date(),
            min_value=kp_data['DateTime'].min().date(),
            max_value=kp_data['DateTime'].max().date()
        )
    with col2:
        symbol = st.text_input("Market Symbol", "GOLD").upper()
    
    # Generate and send report
    if st.button("Generate & Send Report"):
        with st.spinner("Creating astro report..."):
            filtered_data = kp_data[kp_data['DateTime'].dt.date == selected_date]
            
            if filtered_data.empty:
                st.error("No data available for selected date")
                return
            
            report = generate_report(symbol, selected_date, filtered_data)
            
            if report:
                st.subheader("Report Preview")
                st.markdown(f"```\n{report}\n```")
                
                success, message = send_to_telegram(report)
                if success:
                    st.balloons()
                    st.success("Report sent to Telegram successfully!")
                    logging.info(f"Sent report for {symbol} on {selected_date}")
                else:
                    st.error(f"Failed to send: {message}")
            else:
                st.error("Failed to generate report")

if __name__ == "__main__":
    main()
