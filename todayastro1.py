import requests
import pandas as pd
from datetime import datetime
import re

# Telegram Configuration (use environment variables in production)
BOT_TOKEN = '7613703350:AAGIvRqgsG_yTcOlFADRSYd_FtoLOPwXDKk'
CHAT_ID = '-1002840229810'

# Other Configuration
KP_ASTRO_FILE = 'kp_astro.txt'
DEEPSEEK_API_URL = 'https://api.deepseek.com/v1/chat/completions'  # Example, verify actual API endpoint

def read_kp_astro_data(file_path):
    """Read and parse KP Astrology data from text file"""
    columns = ["Planet", "Date", "Time", "Motion", "Sign Lord", "Star Lord", 
               "Sub Lord", "Zodiac", "Nakshatra", "Pada", "Pos in Zodiac", "Declination"]
    
    data = []
    with open(file_path, 'r') as file:
        for line in file:
            if line.strip():
                parts = re.split(r'\t|\s{2,}', line.strip())
                if len(parts) >= len(columns):
                    data.append(parts[:len(columns)])
    
    df = pd.DataFrame(data, columns=columns)
    df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'])
    return df

def generate_astro_prompt(stock_symbol, kp_data):
    """Generate a detailed prompt for AI analysis"""
    today = datetime.now().date()
    date_range = [today.strftime('%Y-%m-%d'), 
                 (today + pd.Timedelta(days=1)).strftime('%Y-%m-%d'),
                 (today + pd.Timedelta(days=2)).strftime('%Y-%m-%d')]
    
    filtered_data = kp_data[kp_data['Date'].isin(date_range)]
    
    prompt = f"""
    As an expert in both KP astrology and financial markets, analyze this planetary data to predict:
    - Bullish/bearish periods for {stock_symbol}
    - Optimal entry/exit points
    - Key support/resistance levels astrologically indicated
    
    Timeframe: Next 3 days ({', '.join(date_range)})
    
    KP Astrology Data:
    {filtered_data.to_string(index=False)}
    
    Required Analysis:
    1. Overall Market Trend (Strong Bullish/Moderate Bullish/Neutral/Moderate Bearish/Strong Bearish)
    2. Hourly/Daily Favorable Periods (With Confidence %)
    3. Critical Planetary Aspects Affecting Prices
    4. Recommended Trading Strategy
    5. Important Risk Factors
    
    Provide specific astrological justifications for each prediction.
    """
    return prompt

def query_ai_analysis(prompt):
    """Query AI for analysis (mock implementation - replace with actual API call)"""
    # Example of actual API call (uncomment and configure when you have API details):
    """
    headers = {
        'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': 'deepseek-chat',
        'messages': [{'role': 'user', 'content': prompt}],
        'temperature': 0.7
    }
    response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload)
    return response.json()['choices'][0]['message']['content']
    """
    
    # Mock response for testing
    return f"""
📊 KP Astro-Financial Analysis Report

1. Overall Trend: Moderate Bullish (65% confidence)
- Jupiter in Mrigashira supports upward movement
- Venus-Moon conjunction enhances trading volume

2. Key Time Windows:
✅ Strong Buy: Today 11:30-13:45 (Moon-Jupiter trine)
⚠️ Caution: Tomorrow 15:00-16:30 (Saturn aspect)

3. Critical Aspects:
- Mercury in Gemini: High volatility in tech stocks
- Mars sub-period: Aggressive trading patterns expected

4. Strategy:
- Accumulate during early bullish periods
- Take profits during Saturn aspects
- Stop-loss at 2% below entry during volatile phases

5. Risk Factors:
- Moon in Chitra 3rd pada increases unpredictability
- Watch for news triggers during Mercury sub-periods
"""

def send_telegram_message(text):
    """Send formatted message to Telegram channel"""
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {
        'chat_id': CHAT_ID,
        'text': text,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")
        return False

def main():
    print("KP Astrology Stock Analysis System")
    print("=================================\n")
    
    try:
        # Load data
        kp_data = read_kp_astro_data(KP_ASTRO_FILE)
        stock_symbol = input("Enter stock symbol (e.g., NIFTY, SBI): ").strip().upper()
        
        # Generate analysis
        prompt = generate_astro_prompt(stock_symbol, kp_data)
        print("\nGenerating AI analysis...")
        analysis = query_ai_analysis(prompt)
        
        # Format message
        message = f"""
<b>✨ KP Astro-Trading Analysis for {stock_symbol} ✨</b>
<i>Generated at {datetime.now().strftime('%Y-%m-%d %H:%M')}</i>

{analysis}

<code>Disclaimer: For educational purposes only. Consult a financial advisor before trading.</code>
        """.strip()
        
        # Send to Telegram
        print("\nSending to Telegram...")
        if send_telegram_message(message):
            print("Successfully sent to Telegram channel!")
        else:
            print("Failed to send to Telegram. Check your configurations.")
            
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    main()
