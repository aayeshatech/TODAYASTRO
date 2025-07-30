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

# ========== Enhanced KP Astro Parser ==========
def parse_kp_astro(file_path):
    """Parse the KP Astro data file with proper error handling"""
    try:
        data = []
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('Planet'):
                    continue
                
                # Handle variable whitespace and tab separation
                parts = re.split(r'\s+', line)
                if len(parts) < 11:  # Minimum required columns
                    continue
                
                # Extract date and time components
                date_part = parts[1]
                time_part = parts[2]
                
                try:
                    # Parse datetime with error handling
                    dt_str = f"{date_part} {time_part}"
                    date_time = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
                except ValueError as e:
                    logging.warning(f"Skipping line due to datetime error: {line} | Error: {str(e)}")
                    continue
                
                # Build data record
                record = {
                    'Planet': parts[0],
                    'DateTime': date_time,
                    'Motion': parts[3],
                    'Sign_Lord': parts[4],
                    'Star_Lord': parts[5],
                    'Sub_Lord': parts[6],
                    'Zodiac': parts[7],
                    'Nakshatra': parts[8],
                    'Pada': parts[9],
                    'Position': parts[10],
                    'Declination': parts[11] if len(parts) > 11 else ''
                }
                data.append(record)
        
        return pd.DataFrame(data)
    
    except Exception as e:
        logging.error(f"File parsing error: {str(e)}")
        st.error(f"Error parsing file: {str(e)}")
        return pd.DataFrame()

# ========== Streamlit UI ==========
def main():
    st.set_page_config(page_title="Aayeshatech Astro Alerts", layout="wide")
    st.title("📡 Astro Trading Telegram Alerts")
    
    # File upload section
    uploaded_file = st.file_uploader("Upload kp astro.txt", type="txt")
    if uploaded_file is not None:
        try:
            # Save uploaded file
            with open("kp astro.txt", "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success("File uploaded successfully!")
        except Exception as e:
            st.error(f"Error saving file: {str(e)}")
    
    if not os.path.exists("kp astro.txt"):
        st.warning("Please upload kp astro.txt file")
        return
    
    # Parse the data file
    kp_df = parse_kp_astro("kp astro.txt")
    
    if kp_df.empty:
        st.error("No valid data found in the file. Please check the format.")
        st.info("Expected format: Planet Date Time Motion Sign_Lord Star_Lord Sub_Lord Zodiac Nakshatra Pada Position Declination")
        return
    
    # Show parsed data
    st.subheader("Parsed Data Preview")
    st.dataframe(kp_df.head())
    
    # Debug information
    with st.expander("Debug Info"):
        st.write(f"Total records: {len(kp_df)}")
        st.write(f"Date range: {kp_df['DateTime'].min()} to {kp_df['DateTime'].max()}")
        st.write("Column types:", kp_df.dtypes)

if __name__ == "__main__":
    main()
