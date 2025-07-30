import pandas as pd
from datetime import datetime
import re
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def parse_kp_astro_data(file_path):
    """Robust parser for KP Astrology data"""
    columns = ["Planet", "Date", "Time", "Motion", "Sign Lord", "Star Lord", 
               "Sub Lord", "Zodiac", "Nakshatra", "Pada", "Pos in Zodiac", "Declination"]
    
    data = []
    with open(file_path, 'r') as file:
        for line in file:
            if line.strip():
                # Handle both tab and space delimiters
                parts = re.split(r'\t|\s{2,}', line.strip())
                if len(parts) >= len(columns):
                    data.append(parts[:len(columns)])
    
    df = pd.DataFrame(data, columns=columns)
    
    # Clean and convert datetime with explicit format
    try:
        # Remove any non-standard characters from time
        df['Time'] = df['Time'].str.replace(r'[^\d:]', '', regex=True)
        
        # Combine date and time with explicit format
        datetime_str = df['Date'] + ' ' + df['Time']
        df['DateTime'] = pd.to_datetime(datetime_str, 
                                       format='%Y-%m-%d %H:%M:%S', 
                                       errors='coerce')
        
        # Verify we have valid datetimes
        if df['DateTime'].isnull().any():
            print("Warning: Some dates couldn't be parsed. Sample problematic rows:")
            print(df[df['DateTime'].isnull()].head(2))
    except Exception as e:
        print(f"DateTime parsing error: {str(e)}")
        raise
    
    return df

def main():
    print("KP Astrology Stock Analysis System")
    print("=================================\n")
    
    try:
        # 1. Load and parse data
        data_file = 'kp_astro.txt'  # Update with your actual path
        if not os.path.exists(data_file):
            raise FileNotFoundError(f"Data file not found: {data_file}")
        
        print(f"Loading data from {data_file}...")
        kp_data = parse_kp_astro_data(data_file)
        
        # 2. Show data verification
        print("\nData loaded successfully. Sample:")
        print(kp_data[['Planet', 'DateTime', 'Zodiac', 'Nakshatra']].head(3))
        print(f"\nTime range: {kp_data['DateTime'].min()} to {kp_data['DateTime'].max()}")
        
        # 3. Continue with your analysis...
        stock_symbol = input("\nEnter stock symbol (e.g., NIFTY, SBI): ").strip().upper()
        print(f"\nStarting analysis for {stock_symbol}...")
        
        # [Add your analysis logic here]
        
        print("\nAnalysis completed successfully!")
        
    except Exception as e:
        print(f"\nError occurred: {str(e)}")
        print("Stopping...")

if __name__ == "__main__":
    main()
