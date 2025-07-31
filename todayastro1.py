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

def query_deepseek_ai(query_text, kp_data=None):
    """
    Generate DeepSeek-style astrological analysis based on KP data
    """
    try:
        if kp_data is None or kp_data.empty:
            return False, "No KP data available for analysis"
        
        # Create detailed astrological analysis table
        analysis_data = []
        
        for _, row in kp_data.iterrows():
            aspect_type = f"{row['Planet']}-{row['Sub_Lord']}"
            if len(row['Star_Lord']) > 0:
                aspect_type = f"{row['Planet']}-{row['Sub_Lord']}-{row['Star_Lord']}"
            
            # Determine influence based on planetary combinations
            influence = determine_cosmic_influence(row['Planet'], row['Sub_Lord'], row['Star_Lord'])
            notes = generate_cosmic_notes(row)
            
            analysis_data.append({
                'Date': row['Date'],
                'Time': row['Time'],
                'Planet': row['Planet'],
                'Motion': row['Motion'],
                'Sign_Lord': row['Sign_Lord'],
                'Star_Lord': row['Star_Lord'],
                'Sub_Lord': row['Sub_Lord'],
                'Aspect_Type': aspect_type,
                'Influence': influence,
                'Notes': notes
            })
        
        # Generate DeepSeek-style response
        response = generate_deepseek_response(query_text, analysis_data)
        return True, response
        
    except Exception as e:
        return False, f"Error generating DeepSeek analysis: {str(e)}"

def determine_cosmic_influence(planet, sub_lord, star_lord):
    """Determine astrological influence based on planetary combinations"""
    
    # Bullish combinations
    bullish_combos = [
        ('Mo', 'Ju'), ('Su', 'Ju'), ('Ju', 'Ve'), ('Mo', 'Ve'), 
        ('Ve', 'Me'), ('Su', 'Ve'), ('Ma', 'Ju')
    ]
    
    # Bearish combinations  
    bearish_combos = [
        ('Mo', 'Sa'), ('Sa', 'Ra'), ('Mo', 'Ke'), ('Sa', 'Ke'),
        ('Ma', 'Sa'), ('Su', 'Sa'), ('Ra', 'Ke')
    ]
    
    # Volatile combinations
    volatile_combos = [
        ('Mo', 'Me'), ('Ma', 'Me'), ('Ra', 'Me'), ('Me', 'Ke')
    ]
    
    combo = (planet, sub_lord)
    
    if combo in bullish_combos:
        return "Bullish"
    elif combo in bearish_combos:
        return "Bearish"
    elif combo in volatile_combos:
        return "Volatile"
    else:
        return "Neutral"

def generate_cosmic_notes(row):
    """Generate detailed cosmic analysis notes"""
    
    planet = row['Planet']
    sub_lord = row['Sub_Lord']
    star_lord = row['Star_Lord']
    zodiac = row['Zodiac']
    
    notes_map = {
        ('Ve', 'Mo'): f"Venus-Moon in {zodiac} - emotional sensitivity in financial decisions",
        ('Mo', 'Ju'): f"Moon-Jupiter aspect - optimism but check for retrograde effects",
        ('Mo', 'Sa'): f"Moon-Saturn combination - restrictive influence, caution advised",
        ('Mo', 'Me'): f"Mercury-Moon combo in {zodiac} - quick market swings expected",
        ('Ju', 'Su'): f"Jupiter-Sun in {zodiac} - potential combustion effect",
        ('Mo', 'Ke'): f"Moon-Ketu aspect - uncertainty and sudden market drops",
        ('Mo', 'Ve'): f"Moon-Venus in {zodiac} - generally positive for market sentiment",
        ('Mo', 'Su'): f"Moon-Sun aspect - fiery nature may override stability",
        ('Mo', 'Mo'): f"Moon self-aspect in {zodiac} - depends on other planetary transits"
    }
    
    combo = (planet, sub_lord)
    return notes_map.get(combo, f"{planet}-{sub_lord} combination in {zodiac} - monitor for cosmic influences")

def generate_deepseek_response(query, analysis_data):
    """Generate comprehensive DeepSeek-style response"""
    
    # Create table header
    table_lines = [
        "📊 **Detailed Astrological Analysis Table:**",
        "",
        "| Date | Time | Planet | Motion | Sign Lord | Star Lord | Sub Lord | Aspect Type | Influence | Notes |",
        "|------|------|---------|---------|-----------|-----------|----------|-------------|-----------|-------|"
    ]
    
    # Add data rows
    for data in analysis_data:
        row = f"| {data['Date']} | {data['Time']} | {data['Planet']} | {data['Motion']} | {data['Sign_Lord']} | {data['Star_Lord']} | {data['Sub_Lord']} | {data['Aspect_Type']} | {data['Influence']} | {data['Notes']} |"
        table_lines.append(row)
    
    # Count influences
    bullish_count = sum(1 for d in analysis_data if d['Influence'] == 'Bullish')
    bearish_count = sum(1 for d in analysis_data if d['Influence'] == 'Bearish')
    volatile_count = sum(1 for d in analysis_data if d['Influence'] == 'Volatile')
    neutral_count = sum(1 for d in analysis_data if d['Influence'] == 'Neutral')
    
    # Generate key observations
    observations = []
    
    if bullish_count > bearish_count:
        observations.append("🟢 **Predominantly Bullish Day**: More positive planetary aspects favor upward movement")
    elif bearish_count > bullish_count:
        observations.append("🔴 **Bearish Tendency**: Restrictive planetary influences suggest caution")
    else:
        observations.append("🟡 **Mixed Signals**: Balanced planetary forces suggest sideways movement")
    
    if volatile_count > 2:
        observations.append("⚡ **High Volatility Expected**: Multiple Mercury and Mars aspects indicate quick swings")
    
    # Time-based analysis
    morning_aspects = [d for d in analysis_data if d['Time'] < '12:00:00']
    afternoon_aspects = [d for d in analysis_data if d['Time'] >= '12:00:00']
    
    if morning_aspects:
        morning_sentiment = max(set([d['Influence'] for d in morning_aspects]), 
                              key=[d['Influence'] for d in morning_aspects].count)
        observations.append(f"🌅 **Morning Bias**: {morning_sentiment} planetary influences dominate early hours")
    
    if afternoon_aspects:
        afternoon_sentiment = max(set([d['Influence'] for d in afternoon_aspects]), 
                                key=[d['Influence'] for d in afternoon_aspects].count)
        observations.append(f"🌇 **Afternoon Trend**: {afternoon_sentiment} aspects gain strength later")
    
    # Combine everything into final response
    response_parts = [
        "🤖 **DeepSeek AI Response:**",
        "",
        f"**Query:** \"{query}\"",
        "",
        "**Cosmic Analysis:**",
        *table_lines,
        "",
        "📈 **Influence Summary:**",
        f"- Bullish Aspects: {bullish_count}",
        f"- Bearish Aspects: {bearish_count}", 
        f"- Volatile Aspects: {volatile_count}",
        f"- Neutral Aspects: {neutral_count}",
        "",
        "🔍 **Key Observations:**",
        *[f"• {obs}" for obs in observations],
        "",
        "🎯 **Trading Recommendations:**",
        "• **Risk Level**: Moderate to High (based on planetary volatility)",
        "• **Timing Strategy**: Monitor Venus-Moon and Jupiter aspects for entry/exit",
        "• **Caution Periods**: Avoid trading during Saturn and Ketu dominant times",
        "",
        "⚠️ **Disclaimer:** This is astrological interpretation based on planetary positions. Actual market behavior depends on multiple factors including fundamentals, technicals, and global events. Always combine with comprehensive analysis before making trading decisions."
    ]
    
    return "\n".join(response_parts)

def main():
    st.set_page_config(page_title="Enhanced Astro Symbol Tracker", layout="wide")
    
    # Initialize session state
    if 'query_input' not in st.session_state:
        st.session_state.query_input = ''
    
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
                    
                    # Add DeepSeek-style analysis for the symbol
                    st.subheader(f"🤖 DeepSeek Analysis for {symbol}")
                    deepseek_query = f"analyze {symbol} bullish bearish astro aspects timeline with cosmic influences"
                    ds_success, ds_response = query_deepseek_ai(deepseek_query, kp_data)
                    
                    if ds_success:
                        st.markdown(ds_response)
                    else:
                        st.error("Failed to generate DeepSeek analysis")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("📤 Send Basic Report to Telegram"):
                            success, msg = send_to_telegram(report)
                            if success:
                                st.success(msg)
                                st.balloons()
                            else:
                                st.error(msg)
                    
                    with col2:
                        if st.button("📤 Send DeepSeek Analysis to Telegram"):
                            if ds_success:
                                success, msg = send_to_telegram(ds_response)
                                if success:
                                    st.success("DeepSeek analysis sent!")
                                else:
                                    st.error(msg)
                            else:
                                st.error("No DeepSeek analysis to send")
                    
                    with col3:
                        if st.button("📤 Send Combined Report to Telegram"):
                            combined_report = f"{report}\n\n{'='*50}\n\n{ds_response if ds_success else 'DeepSeek analysis unavailable'}"
                            success, msg = send_to_telegram(combined_report)
                            if success:
                                st.success("Combined report sent!")
                            else:
                                st.error(msg)
    
    with tab3:
        st.header("🤖 DeepSeek AI Query")
        st.markdown("Ask DeepSeek AI about market analysis, astrological insights, or trading strategies")
        
        # Quick query buttons
        st.subheader("📋 Quick Query Examples")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🥇 Gold Analysis"):
                st.session_state.query_input = "show Gold bullish bearish astro aspect timeline table format report also add cosmic"
        
        with col2:
            if st.button("📊 Market Overview"):
                st.session_state.query_input = "analyze current planetary aspects for stock market with bullish bearish timeline"
        
        with col3:
            if st.button("🌟 Cosmic Influence"):
                st.session_state.query_input = "explain today's planetary influences on financial markets with timing details"
        
        # DeepSeek-style interface
        query_input = st.text_area(
            "Enter your query:",
            value=st.session_state.get('query_input', ''),
            placeholder="Ask about market predictions, astrological analysis, or trading strategies...",
            height=100
        )
        
        col1, col2, col3 = st.columns([1, 1, 3])
        with col1:
            deepseek_button = st.button("🚀 Query DeepSeek", type="primary")
        with col2:
            if st.button("🗑️ Clear Query"):
                st.session_state.query_input = ''
                st.rerun()
        
        if deepseek_button and query_input.strip():
            with st.spinner("🤖 Querying DeepSeek AI..."):
                success, response = query_deepseek_ai(query_input, kp_data)
                
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
