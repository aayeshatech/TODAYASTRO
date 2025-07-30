import streamlit as st
import pandas as pd
from datetime import datetime
import re
import os
import requests
import pytz

# Telegram Config
BOT_TOKEN = '7613703350:AAGIvRqgsG_yTcOlFADRSYd_FtoLOPwXDKk'
CHAT_ID = '-1002840229810'

# ========== Enhanced KP Astro Parser ==========
def parse_kp_astro(file_path):
    try:
        data = []
        with open(file_path, 'r') as f:
            for line in f:
                if not line.strip() or line.startswith('Planet'):
                    continue
                
                parts = re.split(r'\s+', line.strip())
                if len(parts) < 11:
                    continue
                
                try:
                    date_time = datetime.strptime(f"{parts[1]} {parts[2]}", '%Y-%m-%d %H:%M:%S')
                except:
                    continue
                
                data.append({
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
                })
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error parsing KP astro data: {str(e)}")
        return pd.DataFrame()

# ========== Enhanced Market Analyzer ==========
class AstroMarketAnalyzer:
    def __init__(self, kp_data):
        self.kp_data = kp_data
        self.planet_names = {
            'Mo': 'Moon', 'Su': 'Sun', 'Me': 'Mercury',
            'Ve': 'Venus', 'Ma': 'Mars', 'Ju': 'Jupiter',
            'Sa': 'Saturn', 'Ra': 'Rahu', 'Ke': 'Ketu'
        }
        
    def generate_telegram_report(self, symbol, date):
        if self.kp_data.empty:
            return ""
            
        date_str = date.strftime('%B %d, %Y')
        report = f"🚀 Aayeshatech Astro Trend | {symbol} Price Outlook ({date_str}) 🚀\n\n"
        
        # Convert to IST
        self.kp_data['Time_IST'] = self.kp_data['DateTime'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata').dt.strftime('%I:%M %p')
        
        # Bullish Factors
        bullish = self._get_aspects(['Ju', 'Ve'], ['Mo', 'Su'])
        if not bullish.empty:
            report += "📈 Bullish Factors:\n"
            for _, row in bullish.iterrows():
                desc = self._get_aspect_description(row)
                report += f"✅ {row['Time_IST']} - {desc}\n"
            report += "\n"
        
        # Bearish Factors
        bearish = self._get_aspects(['Sa', 'Ra', 'Ke', 'Ma'], ['Mo', 'Su'])
        if not bearish.empty:
            report += "📉 Bearish Factors:\n"
            for _, row in bearish.iterrows():
                desc = self._get_aspect_description(row)
                report += f"⚠️ {row['Time_IST']} - {desc}\n"
            report += "\n"
        
        # Neutral Factors
        neutral = self._get_aspects(['Me'], ['Mo'])
        if not neutral.empty:
            report += "🔄 Neutral/Volatile:\n"
            for _, row in neutral.iterrows():
                desc = self._get_aspect_description(row)
                report += f"🔸 {row['Time_IST']} - {desc}\n"
            report += "\n"
        
        # Trading Strategy
        report += "🎯 Trading Strategy:\n"
        if not bullish.empty:
            best_times = ", ".join(bullish['Time_IST'].head(2).tolist())
            report += f"🔹 Buy Dips: Around {best_times}\n"
        if not bearish.empty:
            sell_times = ", ".join(bearish['Time_IST'].head(2).tolist())
            report += f"🔹 Sell Rallies: After {sell_times}\n"
        
        report += "\nNote: Astro trends suggest volatility, trade with caution."
        return report
    
    def _get_aspects(self, sub_lords, planets):
        filtered = self.kp_data[
            (self.kp_data['Sub_Lord'].isin(sub_lords)) &
            (self.kp_data['Planet'].isin(planets))
        ].sort_values('DateTime')
        return filtered
    
    def _get_aspect_description(self, row):
        planet = self.planet_names.get(row['Planet'], row['Planet'])
        sub_lord = self.planet_names.get(row['Sub_Lord'], row['Sub_Lord'])
        star_lord = self.planet_names.get(row['Star_Lord'], row['Star_Lord'])
        
        descriptions = {
            ('Mo', 'Ju'): "Moon-Jupiter (Optimism in markets)",
            ('Mo', 'Ve'): "Moon-Venus (Recovery expected)",
            ('Su', 'Ju'): "Sun-Jupiter (Strong bullish momentum)",
            ('Mo', 'Sa'): "Moon-Saturn (Downward pressure)",
            ('Mo', 'Ra'): "Moon-Rahu (Risk of panic selling)",
            ('Mo', 'Ma'): "Moon-Mars (Aggressive selling)",
            ('Mo', 'Ke'): "Moon-Ketu (Sharp drop possible)",
            ('Mo', 'Me'): "Moon-Mercury (Sideways movement)",
            ('Su', 'Sa'): "Sun-Saturn (Early volatility)",
            ('Su', 'Ra'): "Sun-Rahu (Market uncertainty)"
        }
        
        return descriptions.get(
            (row['Planet'], row['Sub_Lord']),
            f"{planet}-{sub_lord} under {star_lord} (Watch for movement)"
        )

# ========== Telegram Sender ==========
def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        response = requests.post(url, json=payload)
        return response.status_code == 200
    except Exception as e:
        st.error(f"Failed to send Telegram message: {e}")
        return False

# ========== Streamlit UI ==========
def main():
    st.set_page_config(page_title="Aayeshatech Astro Trading", layout="wide")
    st.title("🌟 Aayeshatech Astro Trading Signals 🌟")
    
    # File upload
    uploaded_file = st.sidebar.file_uploader("Upload kpastro.txt", type="txt")
    if uploaded_file:
        with open("kpastro.txt", "wb") as f:
            f.write(uploaded_file.getbuffer())
    
    if not os.path.exists("kpastro.txt"):
        st.warning("Please upload kpastro.txt file")
        return
    
    # Load data
    kp_df = parse_kp_astro("kpastro.txt")
    if kp_df.empty:
        st.error("Invalid data in kpastro.txt")
        return
    
    # Date and symbol selection
    min_date = kp_df['DateTime'].min().date()
    max_date = kp_df['DateTime'].max().date()
    selected_date = st.date_input("Select date", value=max_date, min_value=min_date, max_value=max_date)
    
    symbol = st.text_input("Enter Symbol (e.g., GOLD, NIFTY)", "GOLD").upper()
    
    # Generate report
    analyzer = AstroMarketAnalyzer(kp_df[kp_df['DateTime'].dt.date == selected_date])
    
    if st.button("Generate Telegram Report"):
        report = analyzer.generate_telegram_report(symbol, selected_date)
        
        st.subheader("Telegram Report Preview")
        st.markdown(f"```\n{report}\n```")
        
        if st.button("Send to Telegram"):
            if send_to_telegram(report):
                st.success("Report sent to Telegram successfully!")
            else:
                st.error("Failed to send report")

if __name__ == "__main__":
    main()
