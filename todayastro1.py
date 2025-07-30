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

# ========== Market Analysis Rules ==========
def get_market_rules(symbol):
    """Return analysis rules based on symbol category"""
    symbol = symbol.upper()
    
    # Default rules (applied to all symbols)
    base_rules = {
        'timeframe': '30T',
        'bullish_aspects': [
            ('Mo','Ju'), ('Mo','Ve'), ('Su','Ju'), ('Su','Ve'),
            ('Ma','Ju'), ('Ma','Ve'), ('Ju',), ('Ve',)
        ],
        'bearish_aspects': [
            ('Mo','Sa'), ('Mo','Ra'), ('Mo','Ke'), ('Mo','Ma'),
            ('Su','Sa'), ('Su','Ra'), ('Su','Ma'),
            ('Ma','Sa'), ('Ma','Ra'), ('Sa',), ('Ra',), ('Ke',)
        ],
        'neutral_aspects': [
            ('Mo','Me'), ('Mo','Su'), ('Su','Me'), ('Ma','Me')
        ]
    }
    
    # Market-specific overrides
    if any(x in symbol for x in ['NIFTY', 'BANKNIFTY', 'SENSEX']):
        return {
            **base_rules,
            'primary_planet': 'Mo',  # Moon drives equities
            'timeframe': '15T',
            'aspect_descriptions': {
                ('Mo','Ju'): "Moon-Jupiter (Optimism in early trade)",
                ('Mo','Ve'): "Moon-Venus (Recovery expected)",
                ('Mo','Sa'): "Moon-Saturn (Downward pressure)",
                ('Mo','Ra'): "Moon-Rahu (Risk of panic selling)"
            }
        }
    elif any(x in symbol for x in ['GOLD', 'SILVER']):
        return {
            **base_rules,
            'primary_planet': 'Su',  # Sun drives precious metals
            'aspect_descriptions': {
                ('Su','Ju'): "Sun-Jupiter (Strong bullish momentum)",
                ('Su','Ve'): "Sun-Venus (Positive sentiment)",
                ('Su','Sa'): "Sun-Saturn (Institutional selling)",
                ('Su','Ra'): "Sun-Rahu (Market uncertainty)"
            }
        }
    elif any(x in symbol for x in ['CRUDEOIL', 'NATURALGAS']):
        return {
            **base_rules,
            'primary_planet': 'Ma',  # Mars drives energy
            'aspect_descriptions': {
                ('Ma','Ju'): "Mars-Jupiter (Price surge likely)",
                ('Ma','Ve'): "Mars-Venus (Short covering rally)",
                ('Ma','Sa'): "Mars-Saturn (Selling pressure)",
                ('Ma','Ra'): "Mars-Rahu (Volatile moves)"
            }
        }
    elif any(x in symbol for x in ['BTC', 'ETH', 'CRYPTO']):
        return {
            **base_rules,
            'primary_planet': 'Ma',  # Mars drives crypto
            'timeframe': '1H',
            'aspect_descriptions': {
                ('Ma','Ju'): "Mars-Jupiter (Aggressive buying)",
                ('Ma','Ve'): "Mars-Venus (Speculative rally)",
                ('Ma','Sa'): "Mars-Saturn (Whale selling)",
                ('Ma','Ra'): "Mars-Rahu (Flash crash risk)"
            }
        }
    else:
        # Default rules for unknown symbols
        return {
            **base_rules,
            'primary_planet': 'Mo',
            'aspect_descriptions': {
                ('Mo','Ju'): "Moon-Jupiter (Bullish momentum)",
                ('Mo','Ve'): "Moon-Venus (Positive sentiment)",
                ('Mo','Sa'): "Moon-Saturn (Bearish pressure)",
                ('Mo','Ra'): "Moon-Rahu (High volatility)"
            }
        }

# ========== Report Generator ==========
def generate_report(symbol, date, kp_data):
    """Generate formatted trading report"""
    try:
        rules = get_market_rules(symbol)
        primary = rules['primary_planet']
        
        # Filter for date and primary planet
        filtered = kp_data[
            (kp_data['DateTime'].dt.date == date) & 
            (kp_data['Planet'] == primary)
        ].copy()
        
        if filtered.empty:
            return None
        
        # Convert times to IST
        filtered['Time_IST'] = filtered['DateTime'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata').dt.strftime('%I:%M %p')
        
        # Initialize report sections
        report = {
            'title': f"🚀 Aayeshatech Astro Trend | {symbol.upper()} Price Outlook ({date.strftime('%B %d, %Y')}) 🚀",
            'bullish': [],
            'bearish': [],
            'neutral': []
        }
        
        # Analyze each aspect
        for _, row in filtered.iterrows():
            aspect_key = (row['Planet'], row['Sub_Lord'])
            desc = rules['aspect_descriptions'].get(
                aspect_key,
                f"{row['Planet']}-{row['Sub_Lord']} (Market movement expected)"
            )
            
            # Categorize based on rules
            if any(all(x in aspect_key for x in combo) for combo in rules['bullish_aspects']):
                report['bullish'].append((row['Time_IST'], desc))
            elif any(all(x in aspect_key for x in combo) for combo in rules['bearish_aspects']):
                report['bearish'].append((row['Time_IST'], desc))
            elif any(all(x in aspect_key for x in combo) for combo in rules['neutral_aspects']):
                report['neutral'].append((row['Time_IST'], desc))
        
        # Generate strategy (limit to top 2 each)
        strategy = []
        if report['bullish']:
            best_times = [x[0] for x in report['bullish'][:2]]
            strategy.append(f"🔹 Buy Dips: Around {', '.join(best_times)}")
        if report['bearish']:
            sell_times = [x[0] for x in report['bearish'][:2]]
            strategy.append(f"🔹 Sell Rallies: After {', '.join(sell_times)}")
        
        # Format final message (consistent format for all symbols)
        sections = [
            report['title'],
            "\n📈 Bullish Factors:" if report['bullish'] else "",
            *[f"✅ {time} - {desc}" for time, desc in report['bullish']],
            "\n📉 Bearish Factors:" if report['bearish'] else "",
            *[f"⚠️ {time} - {desc}" for time, desc in report['bearish']],
            "\n🔄 Neutral/Volatile:" if report['neutral'] else "",
            *[f"🔸 {time} - {desc}" for time, desc in report['neutral']],
            "\n🎯 Trading Strategy:",
            *strategy,
            "\nNote: Astro trends suggest volatility, trade with caution."
        ]
        
        return "\n".join(filter(None, sections))  # Remove empty sections
    
    except Exception as e:
        logging.error(f"Report error for {symbol}: {str(e)}")
        return None

# ========== Streamlit UI ==========
def main():
    st.set_page_config(page_title="Aayeshatech Astro Alerts", layout="wide")
    st.title("📡 Universal Astro Trading Reports")
    
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
        symbol = st.text_input(
            "Enter any symbol (e.g., NIFTY, GOLD, BTC)",
            "NIFTY"
        ).upper()
    
    # Generate report
    if st.button("Generate Report"):
        with st.spinner(f"Creating {symbol} report..."):
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
