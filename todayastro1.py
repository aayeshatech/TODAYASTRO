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

# Aspect interpretations with buy/sell signals
ASPECTS = {
    ('Mo','Ju'): {"type": "bullish", "signal": "BUY", "desc": "Optimism in early trade"},
    ('Mo','Ve'): {"type": "bullish", "signal": "BUY", "desc": "Recovery expected"},
    ('Mo','Sa'): {"type": "bearish", "signal": "SELL", "desc": "Downward pressure"},
    ('Mo','Ra'): {"type": "bearish", "signal": "SELL", "desc": "Risk of panic selling"},
    ('Mo','Ke'): {"type": "bearish", "signal": "SELL", "desc": "Sharp drop possible"},
    ('Mo','Me'): {"type": "neutral", "signal": "HOLD", "desc": "Sideways movement"},
    ('Mo','Su'): {"type": "neutral", "signal": "HOLD", "desc": "Mixed signals"},
    ('Su','Ju'): {"type": "bullish", "signal": "STRONG BUY", "desc": "Strong bullish momentum"},
    ('Su','Ve'): {"type": "bullish", "signal": "BUY", "desc": "Positive sentiment"},
    ('Su','Sa'): {"type": "bearish", "signal": "STRONG SELL", "desc": "Institutional selling"},
    ('Ma','Ju'): {"type": "bullish", "signal": "AGGRESSIVE BUY", "desc": "Aggressive buying"},
    ('Ma','Ve'): {"type": "bullish", "signal": "BUY", "desc": "Speculative rally"},
    ('Ma','Sa'): {"type": "bearish", "signal": "SELL", "desc": "Correction likely"},
    ('Ju','Ve'): {"type": "bullish", "signal": "LONG BUY", "desc": "Sustained uptrend"},
    ('Sa','Ra'): {"type": "bearish", "signal": "AVOID", "desc": "Major decline risk"},
    ('Ra','Ke'): {"type": "bearish", "signal": "EXIT", "desc": "Extreme volatility"}
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
                        'Sub_Lord': parts[6]
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

def generate_trading_report(symbol, date, kp_data):
    """Generate trading report with clear buy/sell signals"""
    try:
        # Filter for selected date
        filtered = kp_data[kp_data['DateTime'].dt.date == date].copy()
        if filtered.empty:
            return None
            
        # Convert times to IST
        filtered['Time_IST'] = filtered['DateTime'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
        filtered['Time_Str'] = filtered['Time_IST'].dt.strftime('%I:%M %p')
        filtered['Hour'] = filtered['Time_IST'].dt.hour
        
        # Generate trading signals
        signals = []
        for _, row in filtered.iterrows():
            aspect_key = (row['Planet'], row['Sub_Lord'])
            if aspect_key in ASPECTS:
                aspect = ASPECTS[aspect_key]
                signals.append({
                    'Time': row['Time_Str'],
                    'Planets': f"{row['Planet']}-{row['Sub_Lord']}",
                    'Signal': aspect['signal'],
                    'Type': aspect['type'],
                    'Description': aspect['desc'],
                    'Hour': row['Hour']
                })
        
        if not signals:
            return None
            
        signals_df = pd.DataFrame(signals)
        
        # Generate report
        report = [
            f"📈 {symbol.upper()} Astro Trading Signals - {date.strftime('%d %b %Y')}",
            "",
            "🕒 Time    | 🔄 Transit      | 📊 Signal        | 📝 Description",
            "――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――"
        ]
        
        # Morning session (9:15 AM to 12:00 PM)
        morning = signals_df[(signals_df['Hour'] >= 9) & (signals_df['Hour'] < 12)]
        if not morning.empty:
            report.append("\n🌅 Morning Session (9:15 AM - 12:00 PM)")
            for _, row in morning.iterrows():
                report.append(f"{row['Time']} | {row['Planets']:8} | {row['Signal']:14} | {row['Description']}")
        
        # Afternoon session (12:00 PM to 3:30 PM)
        afternoon = signals_df[(signals_df['Hour'] >= 12) & (signals_df['Hour'] < 15)]
        if not afternoon.empty:
            report.append("\n🌇 Afternoon Session (12:00 PM - 3:30 PM)")
            for _, row in afternoon.iterrows():
                report.append(f"{row['Time']} | {row['Planets']:8} | {row['Signal']:14} | {row['Description']}")
        
        # Evening session (after market close)
        evening = signals_df[signals_df['Hour'] >= 15]
        if not evening.empty:
            report.append("\n🌃 Evening Session (After 3:30 PM)")
            for _, row in evening.iterrows():
                report.append(f"{row['Time']} | {row['Planets']:8} | {row['Signal']:14} | {row['Description']}")
        
        # Summary of key signals
        strong_buys = signals_df[signals_df['Signal'].str.contains('STRONG BUY|AGGRESSIVE BUY')]
        strong_sells = signals_df[signals_df['Signal'].str.contains('STRONG SELL|AVOID|EXIT')]
        
        report.append("\n🎯 Key Trading Recommendations:")
        if not strong_buys.empty:
            report.append(f"✅ STRONG BUY ZONE: {', '.join(strong_buys['Time'].tolist())}")
        if not strong_sells.empty:
            report.append(f"❌ STRONG SELL ZONE: {', '.join(strong_sells['Time'].tolist())}")
        
        report.append("\n⚠️ Risk Management: Always use stop-loss and proper position sizing")
        
        return "\n".join(report)
    
    except Exception as e:
        st.error(f"Report generation error: {str(e)}")
        return None

def send_to_telegram(message):
    """Improved Telegram sending with retry logic"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    headers = {'Content-Type': 'application/json'}
    
    # Telegram has a 4096 character limit
    if len(message) > 4000:
        message = message[:4000] + "\n...[truncated]"
    
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    }
    
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            
            if response.status_code == 200:
                return True, "Message sent successfully!"
            
            # Handle rate limiting (status code 429)
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', retry_delay))
                st.warning(f"Rate limited. Retrying in {retry_after} seconds...")
                time.sleep(retry_after)
                continue
                
            error_msg = response.json().get('description', 'Unknown error')
            return False, f"Telegram API Error: {error_msg}"
            
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                return False, f"Failed after {max_retries} attempts: {str(e)}"
            time.sleep(retry_delay)
    
    return False, "Unknown error occurred"

def test_telegram_connection():
    """Test if we can connect to Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return True, "✅ Telegram connection successful!"
        return False, f"❌ Telegram connection failed (Status: {response.status_code})"
    except Exception as e:
        return False, f"❌ Connection error: {str(e)}"

def main():
    st.set_page_config(page_title="Astro Trading Signals", layout="wide")
    st.title("✨ Astro Trading Signal Generator")
    
    # Connection test in sidebar
    with st.sidebar:
        st.subheader("Telegram Connection")
        if st.button("Test Telegram Connection"):
            success, msg = test_telegram_connection()
            if success:
                st.success(msg)
            else:
                st.error(msg)
    
    # File upload
    uploaded_file = st.file_uploader("Upload KP Astro Data", type="txt")
    file_path = "kp_astro.txt"
    
    if uploaded_file is not None:
        try:
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success("Data file loaded successfully!")
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
            "Select Trading Date",
            value=kp_df['DateTime'].max().date(),
            min_value=kp_df['DateTime'].min().date(),
            max_value=kp_df['DateTime'].max().date()
        )
    with col2:
        symbol = st.text_input("Market Symbol (e.g. NIFTY, BANKNIFTY, GOLD)", "NIFTY").upper()
    
    # Generate report
    if st.button("Generate Trading Signals"):
        with st.spinner("Analyzing planetary transits..."):
            report = generate_trading_report(symbol, selected_date, kp_df)
            
            if report is None:
                st.error("No significant astro aspects found for selected date")
                return
            
            st.subheader("Astro Trading Signals")
            st.code(report, language='text')
            
            # Store report in session state
            st.session_state.generated_report = report
    
    # Send to Telegram button (only appears after report generation)
    if 'generated_report' in st.session_state:
        if st.button("📤 Send to Telegram"):
            with st.spinner("Sending to Telegram..."):
                success, message = send_to_telegram(st.session_state.generated_report)
                if success:
                    st.success(message)
                    st.balloons()
                else:
                    st.error(f"Failed to send: {message}")
                    
                    # Show troubleshooting tips
                    st.warning("""
                    Telegram Sending Issues? Try:
                    1. Check your bot token and chat ID
                    2. Ensure the bot is added to your channel
                    3. Verify the bot has send message permissions
                    4. Check for internet connectivity
                    5. Try again after a few minutes
                    """)

if __name__ == "__main__":
    main()
