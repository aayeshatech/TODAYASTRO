import swisseph as swe
from datetime import datetime, timedelta
import pytz
import requests
import logging
import pandas as pd

# ========== Constants ==========
RAHU = swe.MEAN_NODE
KETU = swe.TRUE_NODE

# ========== Setup ==========
logging.basicConfig(
    level=logging.INFO,
    filename='astro_market_signals.log',
    format='%(asctime)s - %(levelname)s - %(message)s'
)

try:
    swe.set_ephe_path('/usr/share/ephe')
    swe.set_sid_mode(swe.SIDM_LAHIRI)
except Exception as e:
    logging.error(f"Ephemeris setup error: {e}")
    raise

# Telegram config
BOT_TOKEN = '7613703350:AAGIvRqgsG_yTcOlFADRSYd_FtoLOPwXDKk'
CHAT_ID = '-1002840229810'

# ========== Market Groups ==========
EQUITY_MARKETS = {
    'NIFTY50': 'NSE:NIFTY',
    'BANKNIFTY': 'NSE:BANKNIFTY',
    'SBIN': 'NSE:SBIN',
    'RELIANCE': 'NSE:RELIANCE'
}

COMMODITY_MARKETS = {
    'GOLD': 'MCX:GOLD',
    'SILVER': 'MCX:SILVER',
    'CRUDEOIL': 'MCX:CRUDEOIL',
    'BTCUSD': 'BINANCE:BTCUSDT',
    'DOW30': 'US:DOW'
}

# ========== Astro Config ==========
BULLISH_PLANETS = [swe.JUPITER, swe.VENUS, swe.MOON]
BEARISH_PLANETS = [swe.SATURN, swe.MARS, RAHU]
NEUTRAL_PLANETS = [swe.MERCURY, KETU]

NAKSHATRA_GROUPS = {
    'bullish': ["Rohini", "Pushya", "Shravana", "Hasta", "Ashwini"],
    'bearish': ["Ardra", "Jyeshtha", "Mula", "Bharani", "Magha"]
}

# ========== Helper Functions ==========
def get_planet_position(jd, planet):
    try:
        pos, flags = swe.calc_ut(jd, planet)
        return {
            'longitude': pos[0],
            'latitude': pos[1],
            'speed': pos[3] if len(pos) > 3 else 0,
            'sign': get_sign_name(pos[0]),
            'nakshatra': get_nakshatra(pos[0])
        }
    except Exception as e:
        logging.error(f"Error getting position for planet {planet}: {e}")
        return None

def get_sign_name(longitude):
    signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
             "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    return signs[int(longitude / 30)]

def get_nakshatra(longitude):
    nakshatras = [
        "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashirsha", "Ardra",
        "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
        "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
        "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta",
        "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
    ]
    longitude = longitude % 360
    return nakshatras[int(longitude / (360/27))]

def get_planet_aspects(jd, planet):
    aspects = []
    for target in [swe.SUN, swe.MOON, swe.MERCURY, swe.VENUS, swe.MARS, 
                   swe.JUPITER, swe.SATURN, RAHU, KETU]:
        if planet == target:
            continue
        
        try:
            pos1 = swe.calc_ut(jd, planet)[0]
            pos2 = swe.calc_ut(jd, target)[0]
            aspect_degree = abs(pos1 - pos2) % 360
            if aspect_degree > 180:
                aspect_degree = 360 - aspect_degree
            
            if aspect_degree < 8:  # Tight orb for significant aspects
                aspects.append({
                    'planet': target,
                    'degree': aspect_degree,
                    'type': get_aspect_type(planet, target)
                })
        except Exception as e:
            logging.error(f"Aspect calculation error: {e}")
    
    return aspects

def get_aspect_type(planet1, planet2):
    if planet1 in BULLISH_PLANETS and planet2 in BULLISH_PLANETS:
        return 'harmonious'
    elif planet1 in BEARISH_PLANETS and planet2 in BEARISH_PLANETS:
        return 'stressful'
    else:
        return 'neutral'

def analyze_market_sentiment(jd, market_type):
    try:
        if market_type == 'equity':
            planet = swe.MOON  # Equities are Moon-sensitive
        else:
            planet = swe.SUN  # Commodities are Sun-sensitive
        
        position = get_planet_position(jd, planet)
        if position is None:
            return '⚪ ERROR'
        
        aspects = get_planet_aspects(jd, planet)
        
        bull_factor = 0
        bear_factor = 0
        
        # Aspect analysis
        for aspect in aspects:
            if aspect['type'] == 'harmonious':
                bull_factor += 2 if aspect['degree'] < 3 else 1
            elif aspect['type'] == 'stressful':
                bear_factor += 2 if aspect['degree'] < 3 else 1
        
        # Nakshatra influence
        if position['nakshatra'] in NAKSHATRA_GROUPS['bullish']:
            bull_factor += 1
        elif position['nakshatra'] in NAKSHATRA_GROUPS['bearish']:
            bear_factor += 1
        
        # Determine final signal
        if bull_factor > bear_factor + 2:
            return '🟢 STRONG BULLISH'
        elif bull_factor > bear_factor:
            return '🟢 Mild Bullish'
        elif bear_factor > bull_factor + 2:
            return '🔴 STRONG BEARISH'
        elif bear_factor > bull_factor:
            return '🔴 Mild Bearish'
        else:
            return '⚪ NEUTRAL'
    except Exception as e:
        logging.error(f"Sentiment analysis error: {e}")
        return '⚪ ERROR'

def generate_signal_table(start_dt, hours=24):
    signals = []
    current = start_dt
    end = start_dt + timedelta(hours=hours)
    
    while current <= end:
        try:
            jd = swe.julday(current.year, current.month, current.day, 
                           current.hour + current.minute/60)
            
            signals.append({
                'Timestamp': current,
                'Equity_Signal': analyze_market_sentiment(jd, 'equity'),
                'Commodity_Signal': analyze_market_sentiment(jd, 'commodity'),
                'Moon_Pos': get_planet_position(jd, swe.MOON),
                'Sun_Pos': get_planet_position(jd, swe.SUN)
            })
        except Exception as e:
            logging.error(f"Signal generation error at {current}: {e}")
        
        current += timedelta(minutes=30)
    
    return pd.DataFrame(signals)

def generate_transit_timeline(start_dt, hours=24):
    timeline = []
    current = start_dt
    end = start_dt + timedelta(hours=hours)
    
    while current <= end:
        try:
            jd = swe.julday(current.year, current.month, current.day,
                           current.hour + current.minute/60)
            
            # Check all planets
            for planet in [swe.SUN, swe.MOON, swe.MERCURY, swe.VENUS, swe.MARS,
                          swe.JUPITER, swe.SATURN, RAHU, KETU]:
                aspects = get_planet_aspects(jd, planet)
                for aspect in aspects:
                    if aspect['degree'] < 5:  # Only strongest aspects
                        timeline.append({
                            'Time': current,
                            'Planet': swe.get_planet_name(planet),
                            'Aspect': swe.get_planet_name(aspect['planet']),
                            'Degree': aspect['degree'],
                            'Type': aspect['type'],
                            'Intensity': 'STRONG' if aspect['degree'] < 3 else 'MODERATE'
                        })
            
            # Check for sign changes
            for planet in [swe.MOON, swe.MERCURY, swe.VENUS, swe.MARS]:
                pos_now = swe.calc_ut(jd, planet)[0]
                pos_next = swe.calc_ut(jd + 0.001, planet)[0]
                if int(pos_now/30) != int(pos_next/30):
                    timeline.append({
                        'Time': current,
                        'Planet': swe.get_planet_name(planet),
                        'Aspect': f"Entering {get_sign_name(pos_next)}",
                        'Type': 'sign_change',
                        'Intensity': 'STRONG'
                    })
                    
        except Exception as e:
            logging.error(f"Transit timeline error at {current}: {e}")
        
        current += timedelta(minutes=15)  # Check every 15 minutes
    
    return pd.DataFrame(timeline)

def send_telegram_alert(market, symbol, signal_df, transit_df):
    try:
        # Prepare basic info
        now = datetime.now(pytz.utc)
        next_4hr = now + timedelta(hours=4)
        
        # Get relevant signals
        upcoming_signals = signal_df[
            (signal_df['Timestamp'] >= now) & 
            (signal_df['Timestamp'] <= next_4hr)
        ]
        
        # Get critical transits
        critical_transits = transit_df[
            (transit_df['Time'] >= now) & 
            (transit_df['Time'] <= next_4hr) & 
            (transit_df['Intensity'] == 'STRONG')
        ].sort_values('Time').head(5)
        
        # Determine current signal
        if market in EQUITY_MARKETS:
            current_signal = upcoming_signals.iloc[0]['Equity_Signal']
            current_pos = upcoming_signals.iloc[0]['Moon_Pos']
        else:
            current_signal = upcoming_signals.iloc[0]['Commodity_Signal']
            current_pos = upcoming_signals.iloc[0]['Sun_Pos']
        
        # Build message
        message = f"""
📈 *{market} Astro Trading Signal* ({symbol})
⏰ Next 4 Hours: *{current_signal}*
📍 Current: {current_pos['sign']} ({current_pos['nakshatra']})

🔭 *Planetary Positions:*
- Sun: {get_planet_position(swe.julday(now.year, now.month, now.day), swe.SUN)['nakshatra']}
- Moon: {get_planet_position(swe.julday(now.year, now.month, now.day), swe.MOON)['nakshatra']}
- Jupiter: {get_planet_position(swe.julday(now.year, now.month, now.day), swe.JUPITER)['sign']}

🕒 *Critical Aspects Timeline:*
"""
        for _, transit in critical_transits.iterrows():
            emoji = "🟢" if transit['Type'] == 'harmonious' else "🔴"
            action = "BUY" if transit['Type'] == 'harmonious' else "SELL"
            
            message += f"""
{emoji} *{transit['Time'].astimezone(pytz.timezone('Asia/Kolkata')).strftime('%H:%M')} IST*
- {transit['Planet']} → {transit['Aspect']} ({transit['Degree']:.1f}°)
- *Action*: {action} ({transit['Intensity']})
"""
        
        # Add trading strategy
        message += f"""
💡 *Trading Strategy:*
- Strong {('BUY' if 'BULLISH' in current_signal else 'SELL')} during green periods
- Use tight stops during volatile aspects
- Best entries during Moon-Jupiter aspects
"""
        
        # Send message
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                'chat_id': CHAT_ID,
                'text': message,
                'parse_mode': 'Markdown'
            },
            timeout=10
        )
        logging.info(f"Sent alert for {market} (Status: {response.status_code})")
    
    except Exception as e:
        logging.error(f"Failed to send alert for {market}: {e}")

# ========== Main Execution ==========
if __name__ == "__main__":
    try:
        # Initialize
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        
        # Generate data
        logging.info("Generating astro signals...")
        signal_df = generate_signal_table(now)
        transit_df = generate_transit_timeline(now)
        
        # Send alerts
        logging.info("Sending alerts...")
        for market, symbol in EQUITY_MARKETS.items():
            send_telegram_alert(market, symbol, signal_df, transit_df)
        
        for market, symbol in COMMODITY_MARKETS.items():
            send_telegram_alert(market, symbol, signal_df, transit_df)
        
        # Save data
        signal_df.to_csv('signals.csv', index=False)
        transit_df.to_csv('transits.csv', index=False)
        logging.info("Process completed successfully")
    
    except Exception as e:
        logging.error(f"Main execution failed: {e}")
        raise
