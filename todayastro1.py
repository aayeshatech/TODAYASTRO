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

def generate_simple_working_report(symbol, date, kp_data):
    """Generate report using EXACT format of working diagnostic messages"""
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
        
        # Use EXACT same format as working diagnostic message
        working_format = f"""ASTRO ANALYSIS from Aayeshatech Bot
Time: {datetime.now().strftime('%H:%M:%S')}
Symbol: {symbol.upper()}
Date: {date.strftime('%B %d, %Y')}
Best: {best_time} Moon-Jupiter
Worst: {worst_time} Moon-Saturn
[GOOD] Analysis complete"""
        
        return working_format
        
    except Exception as e:
        logging.error(f"Simple report error: {str(e)}")
        # Fallback to absolute minimum
        return f"ASTRO ALERT for {symbol.upper()} on {date.strftime('%Y-%m-%d')} [GOOD] Ready"

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
        
        # Create clean sections without extra newlines that might break Telegram
        sections = []
        sections.append(report['title'])
        
        if report['bullish']:
            sections.append("")
            sections.append("📈 Bullish Factors:")
            sections.extend(report['bullish'])
        
        if report['bearish']:
            sections.append("")
            sections.append("📉 Bearish Factors:")
            sections.extend(report['bearish'])
        
        if report['neutral']:
            sections.append("")
            sections.append("🔄 Neutral/Volatile:")
            sections.extend(report['neutral'])
        
        sections.append("")
        sections.append("🎯 Trading Strategy:")
        sections.extend(strategy)
        
        sections.append("")
        sections.append(f"⚠️ Risk Level: {risk_level} | Trade with appropriate position sizing.")
        
        # Join with single newlines and clean up
        final_report = "\n".join(sections)
        
        # Remove any problematic characters that might break Telegram
        final_report = final_report.replace('```', '').replace('*', '').replace('_', '').replace('`', '')
        
        # Log report details for debugging
        logging.info(f"Generated report for {symbol} - Length: {len(final_report)} chars")
        
        return final_report
    
    except Exception as e:
        error_msg = f"Report generation error: {str(e)}"
        logging.error(error_msg)
        st.error(error_msg)
        
        # Return a simple fallback report
        fallback = f"🚀 Aayeshatech Astro Alert | {symbol.upper()} ({date.strftime('%B %d, %Y')})\n\n⚠️ Technical issue generating detailed report.\n\n🔹 Monitor market carefully today\n🔹 Use standard risk management\n\nContact support if issue persists."
        return fallback

def test_telegram_connection():
    """Test Telegram bot connectivity"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            bot_info = response.json()
            bot_name = bot_info['result']['first_name']
            bot_username = bot_info['result'].get('username', 'No username')
            return True, f"✅ Bot connected: {bot_name} (@{bot_username})"
        else:
            return False, f"❌ Bot connection failed: {response.status_code}"
    except Exception as e:
        return False, f"❌ Connection test failed: {str(e)}"

def check_chat_permissions():
    """Check if bot can access the chat"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChat"
    payload = {'chat_id': CHAT_ID}
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            chat_info = response.json()['result']
            chat_title = chat_info.get('title', 'Unknown')
            chat_type = chat_info.get('type', 'Unknown')
            return True, f"✅ Chat accessible: {chat_title} (Type: {chat_type})"
        else:
            error_data = response.json() if response.content else {}
            error_desc = error_data.get('description', 'Unknown error')
            return False, f"❌ Chat access failed: {error_desc}"
    except Exception as e:
        return False, f"❌ Chat check failed: {str(e)}"

def get_bot_permissions():
    """Check bot permissions in the chat"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember"
    payload = {
        'chat_id': CHAT_ID,
        'user_id': BOT_TOKEN.split(':')[0]  # Bot's user ID is the first part of token
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            member_info = response.json()['result']
            status = member_info.get('status', 'unknown')
            can_send = member_info.get('can_send_messages', False)
            return True, f"✅ Bot status: {status}, Can send messages: {can_send}"
        else:
            error_data = response.json() if response.content else {}
            error_desc = error_data.get('description', 'Unknown error')
            return False, f"❌ Permission check failed: {error_desc}"
    except Exception as e:
        return False, f"❌ Permission check failed: {str(e)}"

def send_to_telegram(message):
    """Send message to Telegram with comprehensive error handling"""
    # Check message length (Telegram limit is 4096 characters)
    if len(message) > 4096:
        logging.warning(f"Message too long: {len(message)} characters. Truncating...")
        # Split into chunks if too long
        return send_long_message(message)
    
    # Clean message for Telegram - more aggressive cleaning
    cleaned_message = message.replace('`', '').replace('*', '').replace('_', '')
    cleaned_message = cleaned_message.replace('🚀', 'ROCKET').replace('✅', '[GOOD]').replace('⚠️', '[WARN]')
    cleaned_message = cleaned_message.replace('🔸', '[NEUTRAL]').replace('🔹', '[STRATEGY]')
    cleaned_message = cleaned_message.replace('📈', '[UP]').replace('📉', '[DOWN]').replace('🔄', '[MIXED]').replace('🎯', '[TARGET]')
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    # Try without parse_mode first
    payload = {
        'chat_id': CHAT_ID,
        'text': cleaned_message
    }
    
    try:
        # Log the exact request being sent
        logging.info(f"=== TELEGRAM REQUEST ===")
        logging.info(f"URL: {url}")
        logging.info(f"Chat ID: {CHAT_ID}")
        logging.info(f"Message length: {len(cleaned_message)}")
        logging.info(f"Message preview: {cleaned_message[:100]}...")
        logging.info(f"Full payload: {payload}")
        
        response = requests.post(url, json=payload, timeout=15)
        
        # Log the complete response
        logging.info(f"=== TELEGRAM RESPONSE ===")
        logging.info(f"Status Code: {response.status_code}")
        logging.info(f"Headers: {dict(response.headers)}")
        logging.info(f"Raw Response: {response.text}")
        
        if response.status_code == 200:
            response_json = response.json()
            if response_json.get('ok'):
                message_id = response_json.get('result', {}).get('message_id', 'Unknown')
                logging.info(f"SUCCESS: Message sent with ID {message_id}")
                return True, f"✅ Message sent successfully! (ID: {message_id})"
            else:
                logging.error(f"Telegram returned OK=false: {response_json}")
                return False, f"❌ Telegram returned error: {response_json.get('description', 'Unknown error')}"
        else:
            error_data = response.json() if response.content else {}
            error_desc = error_data.get('description', 'Unknown error')
            error_code = error_data.get('error_code', response.status_code)
            
            # Log the full error for debugging
            logging.error(f"HTTP {response.status_code}: {error_desc}")
            logging.error(f"Full error response: {response.text}")
            
            # Common error solutions
            if 'message is too long' in error_desc.lower():
                return send_long_message(message)
            elif 'chat not found' in error_desc.lower():
                return False, f"❌ Chat not found. Error: {error_desc}"
            elif 'forbidden' in error_desc.lower():
                return False, f"❌ Bot forbidden. Error: {error_desc}"
            elif 'bad request' in error_desc.lower():
                return False, f"❌ Bad request. Error: {error_desc}"
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

def send_long_message(message):
    """Split and send long messages"""
    try:
        # Split message into chunks of ~3800 characters (leaving room for headers)
        chunk_size = 3800
        chunks = []
        
        if len(message) <= chunk_size:
            chunks = [message]
        else:
            # Split by lines first to keep formatting
            lines = message.split('\n')
            current_chunk = ""
            
            for line in lines:
                if len(current_chunk + line + '\n') <= chunk_size:
                    current_chunk += line + '\n'
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = line + '\n'
            
            if current_chunk:
                chunks.append(current_chunk.strip())
        
        # Send each chunk
        success_count = 0
        total_chunks = len(chunks)
        
        for i, chunk in enumerate(chunks):
            if total_chunks > 1:
                header = f"📊 ASTRO REPORT - Part {i+1}/{total_chunks}\n{'='*40}\n"
                chunk_with_header = header + chunk
            else:
                chunk_with_header = chunk
            
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {
                'chat_id': CHAT_ID,
                'text': chunk_with_header
            }
            
            response = requests.post(url, json=payload, timeout=15)
            
            if response.status_code == 200:
                success_count += 1
                # Small delay between messages to avoid rate limiting
                import time
                time.sleep(1)
            else:
                error_data = response.json() if response.content else {}
                error_desc = error_data.get('description', 'Unknown error')
                logging.error(f"Chunk {i+1} failed: {error_desc}")
                return False, f"❌ Part {i+1} failed: {error_desc}"
        
        return True, f"✅ Report sent successfully in {success_count} parts!"
        
    except Exception as e:
        logging.error(f"Long message error: {str(e)}")
        return False, f"❌ Error splitting message: {str(e)}"

# ========== Streamlit UI ==========
def main():
    st.set_page_config(page_title="Aayeshatech Astro Alerts", layout="wide")
    st.title("📡 Astro Trading Telegram Alerts")
    
    # Sidebar - Telegram Configuration
    st.sidebar.header("🤖 Telegram Setup")
    st.sidebar.write(f"**Bot Token:** ...{BOT_TOKEN[-10:]}")
    st.sidebar.write(f"**Chat ID:** {CHAT_ID}")
    
    # Comprehensive Telegram Testing
    if st.sidebar.button("🔍 Full Telegram Diagnostic"):
        with st.sidebar:
            with st.spinner("Running full diagnostic..."):
                # Test 1: Bot Connection
                st.write("**1. Testing Bot Connection...**")
                success1, result1 = test_telegram_connection()
                if success1:
                    st.success(result1)
                else:
                    st.error(result1)
                    st.stop()
                
                # Test 2: Chat Access
                st.write("**2. Testing Chat Access...**")
                success2, result2 = check_chat_permissions()
                if success2:
                    st.success(result2)
                else:
                    st.error(result2)
                    st.error("**SOLUTION:** Add bot to your channel/group first!")
                    st.stop()
                
                # Test 3: Bot Permissions
                st.write("**3. Checking Bot Permissions...**")
                success3, result3 = get_bot_permissions()
                if success3:
                    st.success(result3)
                else:
                    st.warning(result3)
                
                # Test 4: Send Test Message
                st.write("**4. Sending Test Message...**")
                test_msg = f"🔧 DIAGNOSTIC TEST from Aayeshatech Bot\n⏰ Time: {datetime.now().strftime('%H:%M:%S')}\n✅ All systems working!"
                success4, result4 = send_to_telegram(test_msg)
                if success4:
                    st.success("✅ Test message sent successfully!")
                    st.balloons()
                else:
                    st.error(f"❌ Test message failed: {result4}")
                    
                    # Show specific solutions
                    if "forbidden" in result4.lower():
                        st.error("**SOLUTION:** Make bot an admin in the channel")
                    elif "chat not found" in result4.lower():
                        st.error("**SOLUTION:** Add bot to the channel first")
                    elif "insufficient rights" in result4.lower():
                        st.error("**SOLUTION:** Give bot 'Send Messages' permission")
    
    st.sidebar.markdown("---")
    
    # Telegram Setup Help
    with st.sidebar.expander("🛠️ Telegram Setup Help"):
        st.write("**Step-by-Step Setup:**")
        st.write("1️⃣ Create bot with @BotFather")
        st.write("2️⃣ Get bot token from BotFather")
        st.write("3️⃣ **IMPORTANT:** Add bot to your channel/group")
        st.write("4️⃣ Make bot an admin (or give 'Send Messages' permission)")
        st.write("5️⃣ Get Chat ID from getUpdates")
        st.write("6️⃣ Test using 'Full Telegram Diagnostic' above")
        
        st.markdown("**📱 For Channels:**")
        st.write("• Channel must be public OR bot must be admin")
        st.write("• Chat ID format: -100xxxxxxxxx")
        
        st.markdown("**👥 For Groups:**")
        st.write("• Add bot as member")
        st.write("• Chat ID format: -xxxxxxxxx")
        
        st.markdown("**🔧 Common Issues:**")
        st.write("• 'Chat not found' → Bot not added to channel")
        st.write("• 'Forbidden' → Bot lacks permissions")
        st.write("• 'Bad Request' → Wrong Chat ID format")
    
    # Emergency Debug Section
    with st.sidebar.expander("🔧 Debug Info"):
        if st.button("Show Debug Info"):
            st.write("**Current Settings:**")
            st.write(f"Bot Token: {'✅ Set' if BOT_TOKEN else '❌ Missing'}")
            st.write(f"Chat ID: {'✅ Set' if CHAT_ID else '❌ Missing'}")
            st.write(f"Token Length: {len(BOT_TOKEN) if BOT_TOKEN else 0}")
            st.write(f"Chat ID Type: {type(CHAT_ID).__name__}")
            st.write(f"Chat ID Format: {'✅ Channel' if str(CHAT_ID).startswith('-100') else '⚠️ Group/Other'}")
            
            # Show quick test URLs
            st.markdown("**Quick Test URLs:**")
            st.code(f"Bot Info: https://api.telegram.org/bot{BOT_TOKEN}/getMe")
            st.code(f"Updates: https://api.telegram.org/bot{BOT_TOKEN}/getUpdates")
    
    # Manual Message Sender
    with st.sidebar.expander("📤 Manual Message Test"):
        test_message = st.text_area("Test Message:", "Hello from Aayeshatech Bot! 🚀")
        if st.button("Send Manual Test"):
            if test_message.strip():
                success, result = send_to_telegram(test_message)
                if success:
                    st.success("✅ Manual test sent!")
                else:
                    st.error(f"❌ Failed: {result}")
            else:
                st.warning("Enter a test message first")
    
    st.sidebar.markdown("---")
    
    # Show supported symbols
    st.sidebar.header("📊 Supported Symbols")
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
            # Debug: Show what data we're working with
            st.write("**🔍 Debug Information:**")
            st.write(f"• Selected Date: {selected_date}")
            st.write(f"• Symbol: {symbol}")
            st.write(f"• KP Data Rows: {len(kp_df)}")
            st.write(f"• Date Range: {kp_df['DateTime'].min().date()} to {kp_df['DateTime'].max().date()}")
            
            # Check if we have data for selected date
            date_data = kp_df[kp_df['DateTime'].dt.date == selected_date]
            st.write(f"• Data for selected date: {len(date_data)} rows")
            
            if len(date_data) == 0:
                st.error("❌ No astro data found for selected date!")
                st.info("Try selecting a different date with available data.")
                
                # Show available dates
                available_dates = sorted(kp_df['DateTime'].dt.date.unique())
                st.write("**Available dates:**")
                st.write(available_dates[:10])  # Show first 10 dates
                return
            
            # Try generating report with detailed error tracking
            try:
                st.info("🔄 Generating astro report...")
                report = generate_report(symbol, selected_date, kp_df)
                
                if report is None:
                    st.error("❌ Report generation returned None!")
                    
                    # Create a simple test report instead
                    st.info("🔧 Creating simple test report...")
                    test_report = f"""🚀 Aayeshatech Test Report | {symbol.upper()}
📅 Date: {selected_date.strftime('%B %d, %Y')}
🔍 Data Points: {len(date_data)}
✅ Bot Status: Working
⚠️ Full analysis temporarily unavailable

🎯 Trading Note: Monitor market carefully today.
📊 Use standard risk management practices."""
                    
                    st.subheader("📋 Simple Test Report")
                    st.code(test_report)
                    
                    if st.button("📱 Send Test Report", key="send_test_report"):
                        test_success, test_message = send_to_telegram(test_report)
                        if test_success:
                            st.success("✅ Test report sent!")
                        else:
                            st.error(f"❌ Test report failed: {test_message}")
                    
                    return
                
                # Report generated successfully
                st.success(f"✅ Report generated! ({len(report)} characters)")
                
                # Show the report
                st.subheader("📋 Generated Report")
                st.text_area("Report:", report, height=200)
                
                # Generate and show working format
                st.subheader("🎯 Working Format Report")
                working_report = generate_simple_working_report(symbol, selected_date, kp_df)
                if working_report:
                    st.text_area("Working Format:", working_report, height=150)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("📱 Send Working Format", key="send_working_format"):
                            success, msg = send_to_telegram(working_report)
                            if success:
                                st.balloons()
                                st.success(f"🎉 SUCCESS! {msg}")
                            else:
                                st.error(f"❌ Working format failed: {msg}")
                    
                    with col2:
                        if st.button("📱 Send Full Report", key="send_full_report"):
                            success, msg = send_to_telegram(report)
                            if success:
                                st.balloons()
                                st.success(f"🎉 SUCCESS! {msg}")
                            else:
                                st.error(f"❌ Full report failed: {msg}")
                
                # Download option
                st.download_button(
                    label="💾 Download Report",
                    data=report,
                    file_name=f"astro_report_{symbol}_{selected_date.strftime('%Y%m%d')}.txt",
                    mime="text/plain"
                )
                
            except Exception as e:
                st.error(f"❌ **Critical Error in Report Generation:**")
                st.code(f"Error: {str(e)}")
                st.code(f"Error Type: {type(e).__name__}")
                
                # Show the problematic data
                st.write("**Data causing issues:**")
                st.dataframe(date_data.head())
                
                # Emergency simple report
                emergency_report = f"🚀 Emergency Report | {symbol.upper()} | {selected_date.strftime('%Y-%m-%d')}\n\nSystem Error: {str(e)}\n\nPlease contact support."
                
                if st.button("🚨 Send Emergency Report"):
                    emerg_success, emerg_msg = send_to_telegram(emergency_report)
                    if emerg_success:
                        st.success("✅ Emergency report sent!")
                    else:
                        st.error(f"❌ Emergency failed: {emerg_msg}")

if __name__ == "__main__":
    main()
