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

def get_symbol_specific_aspects(symbol):
    """Get symbol-specific aspect interpretations"""
    symbol_config = SYMBOL_RULERS.get(symbol.upper(), SYMBOL_RULERS['DEFAULT'])
    hash_mod = get_symbol_hash_modifier(symbol)
    
    # Base aspect descriptions with symbol-specific variations
    base_aspects = {
        ('Mo','Ju'): ["Optimism in early trade", "Institutional confidence", "Foreign buying interest"],
        ('Mo','Ve'): ["Recovery expected", "Retail investor interest", "Support levels holding"],
        ('Mo','Sa'): ["Downward pressure", "Profit booking", "Resistance at highs"],
        ('Mo','Ra'): ["Risk of panic selling", "Volatility spike", "News-based reactions"],
        ('Mo','Ke'): ["Sharp drop possible", "Technical breakdown", "Stop-loss triggers"],
        ('Mo','Me'): ["Sideways movement", "Consolidation phase", "Mixed signals"],
        ('Mo','Su'): ["Mixed signals", "Leadership uncertainty", "Trend reversal possible"],
        ('Su','Ju'): ["Strong bullish momentum", "Sector leadership", "Breakout potential"],
        ('Su','Ve'): ["Positive sentiment", "Value buying", "Oversold bounce"],
        ('Su','Sa'): ["Institutional selling", "Regulatory concerns", "Long-term weakness"],
        ('Ma','Ju'): ["Aggressive buying", "Momentum surge", "New highs possible"],
        ('Ma','Ve'): ["Speculative rally", "Short covering", "Technical bounce"],
        ('Ma','Sa'): ["Correction likely", "Selling pressure", "Support test"],
        ('Ju','Ve'): ["Sustained uptrend", "Investment grade buying", "Strong fundamentals"],
        ('Sa','Ra'): ["Major decline risk", "Systemic concerns", "Avoid fresh longs"],
        ('Ra','Ke'): ["Extreme volatility", "Unpredictable moves", "Stay cautious"]
    }
    
    # Modify descriptions based on symbol and hash
    symbol_aspects = {}
    for key, descriptions in base_aspects.items():
        idx = (hash_mod + ord(symbol[0])) % len(descriptions)
        symbol_aspects[key] = descriptions[idx]
    
    return symbol_aspects

def calculate_symbol_influence(symbol, planet, sub_lord):
    """Calculate influence strength based on symbol characteristics"""
    symbol_config = SYMBOL_RULERS.get(symbol.upper(), SYMBOL_RULERS['DEFAULT'])
    hash_mod = get_symbol_hash_modifier(symbol)
    
    base_score = 0
    
    # Primary ruler gets highest influence
    if planet == symbol_config['primary'] or sub_lord == symbol_config['primary']:
        base_score += 3
    
    # Secondary ruler gets medium influence
    if planet == symbol_config['secondary'] or sub_lord == symbol_config['secondary']:
        base_score += 2
    
    # Bearish planets for this symbol
    if sub_lord in symbol_config['bearish']:
        base_score -= 2
    
    # Apply symbol-specific strength multiplier
    base_score *= symbol_config['strength']
    
    # Add hash-based variation for uniqueness
    variation = (hash_mod % 10 - 5) * 0.1  # -0.5 to +0.4 variation
    base_score += variation
    
    return base_score

def generate_report(symbol, date, kp_data):
    """Generate symbol-specific trading report"""
    try:
        # Convert input date to datetime.date for comparison
        if isinstance(date, str):
            date = datetime.strptime(date, '%Y/%m/%d').date()
        elif isinstance(date, datetime):
            date = date.date()
        
        # Filter for selected date
        filtered = kp_data[kp_data['DateTime'].dt.date == date].copy()
        if filtered.empty:
            st.warning(f"No data found for selected date: {date}")
            return None
        
        # Convert times to IST
        filtered['Time_IST'] = filtered['DateTime'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata').dt.strftime('%I:%M %p')
        
        # Get symbol-specific aspects
        symbol_aspects = get_symbol_specific_aspects(symbol)
        
        # Initialize report sections
        report = {
            'title': f"🚀 Aayeshatech Astro Trend | {symbol.upper()} Price Outlook ({date.strftime('%B %d, %Y')}) 🚀",
            'bullish': [],
            'bearish': [],
            'neutral': []
        }
        
        # Analyze each entry with symbol-specific logic
        for _, row in filtered.iterrows():
            aspect_key = (row['Planet'], row['Sub_Lord'])
            
            # Get symbol-specific description
            if aspect_key in symbol_aspects:
                desc = f"{row['Planet']}-{row['Sub_Lord']} ({symbol_aspects[aspect_key]})"
            else:
                desc = f"{row['Planet']}-{row['Sub_Lord']} (Market movement expected)"
            
            # Calculate symbol-specific influence
            influence = calculate_symbol_influence(symbol, row['Planet'], row['Sub_Lord'])
            
            # Categorize based on symbol-specific influence
            if influence > 1.5:
                report['bullish'].append(f"✅ {row['Time_IST']} - {desc}")
            elif influence < -1.0:
                report['bearish'].append(f"⚠️ {row['Time_IST']} - {desc}")
            else:
                report['neutral'].append(f"🔸 {row['Time_IST']} - {desc}")
        
        # Sort by time for better readability
        for category in ['bullish', 'bearish', 'neutral']:
            report[category].sort(key=lambda x: datetime.strptime(x.split(' - ')[0][2:].strip(), '%I:%M %p'))
        
        # Generate symbol-specific strategy
        strategy = []
        symbol_config = SYMBOL_RULERS.get(symbol.upper(), SYMBOL_RULERS['DEFAULT'])
        
        if report['bullish']:
            best_times = [x.split(' - ')[0] for x in report['bullish'][:2]]
            if symbol_config['strength'] > 1.2:
                strategy.append(f"🔹 Aggressive Buy: Around {', '.join(best_times)}")
            else:
                strategy.append(f"🔹 Buy Dips: Around {', '.join(best_times)}")
        
        if report['bearish']:
            sell_times = [x.split(' - ')[0] for x in report['bearish'][:2]]
            if symbol_config['strength'] > 1.2:
                strategy.append(f"🔹 Quick Exit: Before {', '.join(sell_times)}")
            else:
                strategy.append(f"🔹 Sell Rallies: After {', '.join(sell_times)}")
        
        # Add symbol-specific risk note
        risk_level = "HIGH" if symbol_config['strength'] > 1.2 else "MODERATE"
        
        # Format final message
        sections = [
            report['title'],
            "\n📈 Bullish Factors:" if report['bullish'] else "",
            *report['bullish'],
            "\n📉 Bearish Factors:" if report['bearish'] else "",
            *report['bearish'],
            "\n🔄 Neutral/Volatile:" if report['neutral'] else "",
            *report['neutral'],
            "\n🎯 Trading Strategy:",
            *strategy,
            f"\n⚠️ Risk Level: {risk_level} | Trade with appropriate position sizing."
        ]
        
        return "\n".join(filter(None, sections))
    
    except Exception as e:
        logging.error(f"Report generation error: {str(e)}")
        st.error(f"Error generating report: {str(e)}")
        return None

def test_telegram_connection():
    """Test Telegram bot connectivity"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            bot_info = response.json()
            return True, f"✅ Bot connected: {bot_info['result']['first_name']}"
        else:
            return False, f"❌ Bot connection failed: {response.status_code}"
    except Exception as e:
        return False, f"❌ Connection test failed: {str(e)}"

def send_to_telegram(message):
    """Send message to Telegram with comprehensive error handling"""
    # Clean message for Telegram
    cleaned_message = message.replace('`', '').replace('*', '').replace('_', '')
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    # Try without parse_mode first
    payload = {
        'chat_id': CHAT_ID,
        'text': cleaned_message
    }
    
    try:
        # Log the attempt
        logging.info(f"Sending to Telegram - Chat ID: {CHAT_ID}")
        
        response = requests.post(url, json=payload, timeout=15)
        
        # Debug response
        logging.info(f"Response status: {response.status_code}")
        logging.info(f"Response content: {response.text}")
        
        if response.status_code == 200:
            return True, "✅ Message sent successfully to Telegram!"
        else:
            error_data = response.json() if response.content else {}
            error_desc = error_data.get('description', 'Unknown error')
            error_code = error_data.get('error_code', response.status_code)
            
            # Common error solutions
            if 'chat not found' in error_desc.lower():
                return False, f"❌ Chat not found. Make sure bot is added to the group/channel. Error: {error_desc}"
            elif 'forbidden' in error_desc.lower():
                return False, f"❌ Bot forbidden. Check bot permissions in the group. Error: {error_desc}"
            elif 'invalid' in error_desc.lower():
                return False, f"❌ Invalid token or chat ID. Error: {error_desc}"
            else:
                return False, f"❌ Telegram API Error ({error_code}): {error_desc}"
            
    except requests.exceptions.Timeout:
        logging.error("Telegram API timeout")
        return False, "❌ Request timeout. Check your internet connection."
    except requests.exceptions.ConnectionError:
        logging.error("Telegram connection error")
        return False, "❌ Cannot connect to Telegram. Check internet connection."
    except requests.exceptions.RequestException as e:
        logging.error(f"Telegram request error: {str(e)}")
        return False, f"❌ Request Error: {str(e)}"
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return False, f"❌ Unexpected Error: {str(e)}"

# ========== Streamlit UI ==========
def main():
    st.set_page_config(page_title="Aayeshatech Astro Alerts", layout="wide")
    st.title("📡 Astro Trading Telegram Alerts")
    
    # Show supported symbols
    st.sidebar.header("Supported Symbols")
    st.sidebar.write("Optimized for:")
    for symbol in SYMBOL_RULERS.keys():
        if symbol != 'DEFAULT':
            st.sidebar.write(f"• {symbol}")
    st.sidebar.write("• Any other symbol (default analysis)")
    
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
        st.info(f"📊 {symbol} Analysis: Primary Ruler: {symbol_config['primary']}, Secondary: {symbol_config['secondary']}, Strength: {symbol_config['strength']}")
    
    # Generate and send report
    if st.button("Generate Report"):
        with st.spinner("Creating symbol-specific astro report..."):
            report = generate_report(symbol, selected_date, kp_df)
            
            if report:
                st.subheader("Report Preview")
                st.markdown(f"```\n{report}\n```")
                
                if st.button("Send to Telegram"):
                    success, message = send_to_telegram(report)
                    if success:
                        st.balloons()
                        st.success("✅ Report sent to Telegram!")
                    else:
                        st.error(f"❌ {message}")
            else:
                st.error("Could not generate report for selected date")

if __name__ == "__main__":
    main()
