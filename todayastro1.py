import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import re
import os

# ========== Page Config ==========
st.set_page_config(
    page_title="Aayeshatech Astro Trading",
    page_icon="📈",
    layout="wide"
)

# ========== KP Astro Data Parser ==========
def parse_kp_astro(file_path):
    try:
        data = []
        with open(file_path, 'r') as f:
            for line in f:
                if not line.strip() or line.startswith('Planet'):
                    continue
                
                # Handle both space and tab separated data
                parts = re.split(r'\s+', line.strip())
                
                # Parse date and time
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

# ========== Market Analysis Engine ==========
class AstroMarketAnalyzer:
    def __init__(self, kp_data):
        self.kp_data = kp_data
        self.bullish_naks = ["Hasta", "Rohini", "Pushya", "Shravana", "Ashwini"]
        self.bearish_naks = ["Ardra", "Jyeshtha", "Mula", "Bharani", "Magha"]
        
        self.bullish_combinations = [
            ('Mo', 'Ju'), ('Ve', 'Ju'), ('Mo', 'Ve'), ('Su', 'Ju')
        ]
        self.bearish_combinations = [
            ('Mo', 'Sa'), ('Ma', 'Sa'), ('Mo', 'Ra'), ('Su', 'Sa')
        ]
    
    def analyze_symbol(self, symbol, start_time=None, end_time=None):
        if self.kp_data.empty:
            return pd.DataFrame()
            
        if start_time is None:
            start_time = self.kp_data['DateTime'].min()
        if end_time is None:
            end_time = self.kp_data['DateTime'].max()
            
        filtered = self.kp_data[
            (self.kp_data['DateTime'] >= start_time) & 
            (self.kp_data['DateTime'] <= end_time)
        ].copy()
        
        results = []
        
        for _, row in filtered.iterrows():
            signal = self._get_signal_strength(row)
            results.append({
                'DateTime': row['DateTime'],
                'Planet': row['Planet'],
                'Nakshatra': row['Nakshatra'],
                'Sign_Lord': row['Sign_Lord'],
                'Star_Lord': row['Star_Lord'],
                'Sub_Lord': row['Sub_Lord'],
                'Signal': signal,
                'Recommendation': self._get_recommendation(signal, row['Planet'])
            })
        
        return pd.DataFrame(results)
    
    def _get_signal_strength(self, row):
        score = 0
        
        # Nakshatra influence
        if row['Nakshatra'] in self.bullish_naks:
            score += 1
        elif row['Nakshatra'] in self.bearish_naks:
            score -= 1
            
        # Planetary combinations
        current_combo = (row['Star_Lord'], row['Sub_Lord'])
        if current_combo in self.bullish_combinations:
            score += 2
        elif current_combo in self.bearish_combinations:
            score -= 2
            
        # Moon specific rules
        if row['Planet'] == 'Mo':
            if row['Sub_Lord'] in ['Ju', 'Ve']:
                score += 1
            elif row['Sub_Lord'] in ['Sa', 'Ra', 'Ke']:
                score -= 1
                
        # Sun specific rules
        if row['Planet'] == 'Su':
            if row['Sub_Lord'] in ['Ju', 'Ve']:
                score += 1
            elif row['Sub_Lord'] in ['Sa', 'Ma']:
                score -= 1
                
        # Determine final signal
        if score >= 2:
            return '🟢 STRONG BULLISH'
        elif score > 0:
            return '🟢 Mild Bullish'
        elif score <= -2:
            return '🔴 STRONG BEARISH'
        elif score < 0:
            return '🔴 Mild Bearish'
        else:
            return '⚪ NEUTRAL'
    
    def _get_recommendation(self, signal, planet):
        recommendations = {
            '🟢 STRONG BULLISH': {
                'Mo': "Excellent buying opportunity (Moon favorable)",
                'Su': "Strong uptrend likely (Sun powerful)",
                'default': "Strong buy signal"
            },
            '🟢 Mild Bullish': {
                'Mo': "Good time to accumulate (Moon supportive)",
                'default': "Moderate buy opportunity"
            },
            '🔴 STRONG BEARISH': {
                'Mo': "Avoid new positions (Moon stressed)",
                'Su': "Market likely to decline (Sun afflicted)",
                'default': "Strong sell signal"
            },
            '🔴 Mild Bearish': {
                'Mo': "Caution advised (Moon uncomfortable)",
                'default': "Consider reducing positions"
            },
            '⚪ NEUTRAL': {
                'Mo': "Wait for clearer signals (Moon transitioning)",
                'default': "Neutral - Wait for confirmation"
            }
        }
        
        return recommendations[signal].get(planet, recommendations[signal]['default'])

# ========== Streamlit UI ==========
def main():
    st.title("🌟 Aayeshatech Astro Trading Signals 🌟")
    st.markdown("""
    <style>
    .big-font { font-size:18px !important; }
    .signal-bullish { color: green; font-weight: bold; }
    .signal-bearish { color: red; font-weight: bold; }
    .signal-neutral { color: gray; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)
    
    # File upload section
    st.sidebar.header("Upload KP Astro Data")
    uploaded_file = st.sidebar.file_uploader("Choose kp astro.txt", type="txt")
    
    if uploaded_file is not None:
        # Save uploaded file
        with open("kp astro.txt", "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.sidebar.success("File uploaded successfully!")
    
    # Check if file exists
    if not os.path.exists("kp astro.txt"):
        st.warning("Please upload kp astro.txt file in the sidebar")
        return
    
    # Load data
    kp_df = parse_kp_astro("kp astro.txt")
    
    if kp_df.empty:
        st.error("No valid data found in kp astro.txt. Please check the file format.")
        return
    
    # Initialize analyzer
    analyzer = AstroMarketAnalyzer(kp_df)
    
    # Date selection
    min_date = kp_df['DateTime'].min().date()
    max_date = kp_df['DateTime'].max().date()
    selected_date = st.date_input(
        "Select date for analysis",
        value=max_date,
        min_value=min_date,
        max_value=max_date
    )
    
    # Symbol selection
    symbols = ['NIFTY', 'BANKNIFTY', 'GOLD', 'CRUDEOIL', 'BTC', 'SILVER']
    selected_symbol = st.selectbox("Select symbol", symbols)
    
    # Analysis button
    if st.button("Generate Trading Signals"):
        with st.spinner("Analyzing planetary positions..."):
            start_time = datetime.combine(selected_date, datetime.min.time())
            end_time = datetime.combine(selected_date, datetime.max.time())
            
            results = analyzer.analyze_symbol(selected_symbol, start_time, end_time)
            
            if results.empty:
                st.warning("No data available for selected date")
                return
            
            # Convert to IST
            results['Time (IST)'] = results['DateTime'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata').dt.strftime('%H:%M')
            
            # Display results
            st.subheader(f"📈 Astro Trading Signals for {selected_symbol} - {selected_date}")
            
            # Summary cards
            bullish = results[results['Signal'].str.contains('BULLISH')]
            bearish = results[results['Signal'].str.contains('BEARISH')]
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Signals", len(results))
            with col2:
                st.metric("Bullish Periods", len(bullish), 
                          f"{bullish['Time (IST)'].min()} to {bullish['Time (IST)'].max()}" if not bullish.empty else "")
            with col3:
                st.metric("Bearish Periods", len(bearish),
                          f"{bearish['Time (IST)'].min()} to {bearish['Time (IST)'].max()}" if not bearish.empty else "")
            
            # Detailed table with styling
            def color_signal(val):
                if 'BULLISH' in val:
                    return 'color: green'
                elif 'BEARISH' in val:
                    return 'color: red'
                return 'color: gray'
            
            st.dataframe(
                results[['Time (IST)', 'Planet', 'Nakshatra', 'Star_Lord', 'Sub_Lord', 'Signal', 'Recommendation']]
                .style.applymap(color_signal, subset=['Signal'])
                .set_properties(**{'text-align': 'left'})
                .format(precision=2),
                height=600
            )
            
            # Trading strategy
            st.subheader("💡 Trading Strategy")
            if not bullish.empty:
                st.markdown(f"""
                **🟢 Best Buying Times:** {bullish['Time (IST)'].min()} to {bullish['Time (IST)'].max()}
                - Look for long entries during these windows
                - Strongest when Moon is with Jupiter or Venus
                """)
            
            if not bearish.empty:
                st.markdown(f"""
                **🔴 Best Selling Times:** {bearish['Time (IST)'].min()} to {bearish['Time (IST)'].max()}
                - Consider profit booking or short positions
                - Especially cautious when Moon is with Saturn or Rahu
                """)
            
            # Download button
            csv = results.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Signals as CSV",
                data=csv,
                file_name=f"{selected_symbol.lower()}_signals_{selected_date}.csv",
                mime='text/csv'
            )

if __name__ == "__main__":
    main()
