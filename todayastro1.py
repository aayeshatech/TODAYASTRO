import pandas as pd
from datetime import datetime
import warnings

# Suppress specific warnings
warnings.filterwarnings('ignore', category=UserWarning, message='Could not infer format')

def parse_datetime_explicitly(df):
    """Explicit datetime parsing with format specification"""
    datetime_format = '%Y-%m-%d %H:%M:%S'  # Adjust based on your actual format
    
    if 'DateTime' in df.columns:
        df['DateTime'] = pd.to_datetime(df['DateTime'], format=datetime_format, errors='coerce')
    if 'Date' in df.columns and 'Time' in df.columns:
        df['DateTime'] = pd.to_datetime(
            df['Date'] + ' ' + df['Time'],
            format='%Y-%m-%d %H:%M:%S',  # Example format, adjust as needed
            errors='coerce'
        )
    return df

def main():
    print("=== Application Initialized ===")
    
    try:
        # 1. Load and process data with explicit datetime format
        df = pd.read_csv('kp_astro.txt', sep='\t')  # Adjust separator as needed
        df = parse_datetime_explicitly(df)
        
        # 2. Add debug output
        print("\nData Sample:")
        print(df.head(3))
        print(f"\nData Shape: {df.shape}")
        
        # 3. Verify time-based calculations
        if 'DateTime' in df.columns:
            print("\nTime Range:", df['DateTime'].min(), "to", df['DateTime'].max())
            
            # Example analysis (replace with your actual logic)
            print("\nPlanetary Motion Summary:")
            print(df['Motion'].value_counts())
        
        # 4. Add explicit completion message
        print("\n=== Analysis Completed Successfully ===")
        
    except Exception as e:
        print(f"\n!!! Error: {str(e)}")
        print("Check your data format and script logic")

if __name__ == "__main__":
    print("Starting application...")
    main()
    print("Application finished")
