import pandas as pd
from datetime import datetime
import pytz
import re

# ========== KP Astro Data Parser ==========
def parse_kp_astro(file_path):
    data = []
    with open(file_path, 'r') as f:
        for line in f:
            if not line.strip() or line.startswith('Planet'):
                continue
            parts = re.split(r'\s+', line.strip())
            
            # Parse date and time
            date_time = datetime.strptime(f"{parts[1]} {parts[2]}", '%Y-%m-%d %H:%M:%S')
            
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
                'Declination': parts[11]
            })
    return pd.DataFrame(data)

# ========== Market Analysis Engine ==========
class AstroMarketAnalyzer:
    def __init__(self, kp_data):
        self.kp_data = kp_data
        self.bullish_naks = ["Hasta", "Rohini", "Pushya", "Shravana"]
        self.bearish_naks = ["Ardra", "Jyeshtha", "Mula", "Bharani"]
        
        self.bullish_combinations = [
            ('Mo', 'Ju'), ('Ve', 'Ju'), ('Mo', 'Ve')
        ]
        self.bearish_combinations = [
            ('Mo', 'Sa'), ('Ma', 'Sa'), ('Mo', 'Ra')
        ]
    
    def analyze_symbol(self, symbol, start_time=None, end_time=None):
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
                'Recommendation': self._get_recommendation(signal)
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
            elif row['Sub_Lord'] in ['Sa', 'Ra']:
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
    
    def _get_recommendation(self, signal):
        if 'STRONG BULLISH' in signal:
            return "Strong Buy Opportunity"
        elif 'Mild Bullish' in signal:
            return "Moderate Buy"
        elif 'STRONG BEARISH' in signal:
            return "Strong Sell Warning"
        elif 'Mild Bearish' in signal:
            return "Moderate Sell"
        else:
            return "Neutral - Wait for confirmation"

# ========== User Interface ==========
def display_results(symbol, results_df):
    print(f"\n📈 Astro Trading Signals for {symbol}")
    print("="*50)
    
    # Convert datetime to IST
    results_df['Time (IST)'] = results_df['DateTime'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata').dt.strftime('%Y-%m-%d %H:%M')
    
    # Display in table format
    display_cols = ['Time (IST)', 'Planet', 'Nakshatra', 'Signal', 'Recommendation']
    print(results_df[display_cols].to_string(index=False))
    
    # Print summary
    bullish_times = results_df[results_df['Signal'].str.contains('BULLISH')]['DateTime']
    bearish_times = results_df[results_df['Signal'].str.contains('BEARISH')]['DateTime']
    
    print("\n💡 Trading Strategy Summary:")
    if not bullish_times.empty:
        print(f"🟢 Best Buy Times: {bullish_times.min().strftime('%H:%M')} to {bullish_times.max().strftime('%H:%M')}")
    if not bearish_times.empty:
        print(f"🔴 Best Sell Times: {bearish_times.min().strftime('%H:%M')} to {bearish_times.max().strftime('%H:%M')}")

# ========== Main Execution ==========
if __name__ == "__main__":
    # Load KP Astro Data
    kp_df = parse_kp_astro('kpastro.txt')
    
    # Initialize analyzer
    analyzer = AstroMarketAnalyzer(kp_df)
    
    # User input
    print("🌟 Aayeshatech Astro Trading Signal Generator 🌟")
    print("Available symbols: NIFTY, BANKNIFTY, GOLD, CRUDEOIL, BTC")
    
    while True:
        symbol = input("\nEnter symbol (or 'quit' to exit): ").upper()
        if symbol == 'QUIT':
            break
            
        if symbol not in ['NIFTY', 'BANKNIFTY', 'GOLD', 'CRUDEOIL', 'BTC']:
            print("Invalid symbol. Please try again.")
            continue
            
        # Get date range input
        date_str = input("Enter date (YYYY-MM-DD) or press enter for today: ")
        try:
            if date_str:
                target_date = datetime.strptime(date_str, '%Y-%m-%d')
            else:
                target_date = datetime.now()
                
            start_time = datetime(target_date.year, target_date.month, target_date.day, 0, 0)
            end_time = datetime(target_date.year, target_date.month, target_date.day, 23, 59)
            
            # Generate signals
            results = analyzer.analyze_symbol(symbol, start_time, end_time)
            
            # Display results
            display_results(symbol, results)
            
            # Save to file
            output_file = f"{symbol.lower()}_signals_{target_date.strftime('%Y%m%d')}.csv"
            results.to_csv(output_file, index=False)
            print(f"\n✅ Results saved to {output_file}")
            
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD.")
