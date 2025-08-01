#!/usr/bin/env python3
"""
Astro Trading Alerts Bot
- Planetary aspect detection
- TradingView integration
- Telegram alerts
"""

import swisseph as swe
from datetime import datetime, timedelta
import time
import pytz
import requests
import logging
import os
from typing import Dict, List, Optional, Tuple

# ===== BOT CONFIGURATION =====
class Config:
    # Telegram Configuration (SECURE THESE CREDENTIALS)
    BOT_TOKEN = '7613703350:AAGIvRqgsG_yTcOlFADRSYd_FtoLOPwXDKk'
    CHAT_ID = '-1002840229810'
    
    # TradingView Configuration
    TRADINGVIEW_API = "https://pro-api.tradingview.com"
    SYMBOLS = {
        "NIFTY": "NSE:NIFTY50",
        "BANKNIFTY": "NSE:BANKNIFTY", 
        "GOLD": "MCX:GOLD"
    }
    API_KEY = os.getenv('TRADINGVIEW_API_KEY', 'your_api_key_here')
    
    # Astrological Configuration
    EPHE_PATH = '/usr/share/ephe'  # Ephemeris files path
    CHECK_INTERVAL = 60  # Check every 60 seconds
    ORB_REDUCTION_DURING_MARKET_HOURS = 0.3  # Tighter orbs during market hours

# ===== INITIALIZATION =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('astro_alerts.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ===== ASTRONOMICAL CONSTANTS =====
PLANETS = {
    'Sun': swe.SUN,
    'Moon': swe.MOON,
    'Mercury': swe.MERCURY,
    'Venus': swe.VENUS,
    'Mars': swe.MARS,
    'Jupiter': swe.JUPITER,
    'Saturn': swe.SATURN,
    'Rahu': swe.MEAN_NODE,
    'Ketu': swe.MEAN_NODE
}

ASPECTS = [
    {'from': 'Jupiter', 'to': 'Sun', 'angle': 120, 'signal': '🟢 STRONG BULLISH', 'orb': 1.5},
    {'from': 'Venus', 'to': 'Moon', 'angle': 0, 'signal': '🟢 BULLISH', 'orb': 1.2},
    {'from': 'Saturn', 'to': 'Mars', 'angle': 90, 'signal': '🔴 STRONG BEARISH', 'orb': 1.5},
    {'from': 'Rahu', 'to': 'Sun', 'angle': 180, 'signal': '🔴 BEARISH', 'orb': 1.8},
    {'from': 'Mars', 'to': 'Mercury', 'angle': 90, 'signal': '🟡 VOLATILE', 'orb': 1.5},
    {'from': 'Rahu', 'to': 'Ketu', 'angle': 180, 'signal': '⚡ MARKET TURNING POINT', 'orb': 0.5}
]

# ===== CORE FUNCTIONS =====
def get_current_ist() -> datetime:
    """Get current Indian Standard Time"""
    return datetime.now(pytz.timezone('Asia/Kolkata')).replace(microsecond=0)

def calculate_planet_positions(jd: float) -> Dict[str, Tuple[float, float]]:
    """Calculate positions for all planets"""
    positions = {}
    try:
        for name, pid in PLANETS.items():
            if name == 'Ketu':
                rahu_pos = swe.calc_ut(jd, PLANETS['Rahu'])[0][0]
                positions['Ketu'] = ((rahu_pos + 180) % 360, 0)
            else:
                positions[name] = swe.calc_ut(jd, pid)[0][:2]  # longitude and latitude
        return positions
    except Exception as e:
        logger.error(f"Planet calculation failed: {str(e)}")
        return None

def detect_aspects(planets: Dict, market_hours: bool) -> List[Dict]:
    """Detect active planetary aspects"""
    if not planets:
        return []

    active_aspects = []
    for aspect in ASPECTS:
        try:
            planet1 = planets.get(aspect['from'])
            planet2 = planets.get(aspect['to'])
            
            if planet1 is None or planet2 is None:
                continue

            angle = abs(planet1[0] - planet2[0]) % 360
            angle = min(angle, 360 - angle)
            effective_orb = aspect['orb'] - (Config.ORB_REDUCTION_DURING_MARKET_HOURS if market_hours else 0)
            
            if abs(angle - aspect['angle']) <= effective_orb:
                active_aspects.append({
                    'aspect': aspect,
                    'actual_angle': angle,
                    'deviation': abs(angle - aspect['angle']),
                    'orb_used': effective_orb
                })
        except Exception as e:
            logger.error(f"Aspect detection error: {str(e)}")
    
    return sorted(active_aspects, key=lambda x: x['deviation'])

def fetch_market_data() -> Dict[str, Dict]:
    """Get current market prices from TradingView"""
    market_data = {}
    for symbol, tv_symbol in Config.SYMBOLS.items():
        try:
            response = requests.get(
                f"{Config.TRADINGVIEW_API}/quote",
                headers={"Authorization": f"Bearer {Config.API_KEY}"},
                params={"symbols": tv_symbol},
                timeout=5
            )
            data = response.json()['data'][0]
            market_data[symbol] = {
                'price': data['last_price'],
                'change': data['change'],
                'change_pct': data['change_percent']
            }
        except Exception as e:
            logger.error(f"Failed to fetch {symbol} data: {str(e)}")
            market_data[symbol] = None
    
    return market_data

def send_telegram_alert(message: str) -> bool:
    """Send formatted message to Telegram"""
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage",
            json={
                'chat_id': Config.CHAT_ID,
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            },
            timeout=10
        )
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Telegram alert failed: {str(e)}")
        return False

def is_market_open() -> bool:
    """Check if Indian stock market is open (Mon-Fri 9:15-15:30 IST)"""
    now = get_current_ist()
    if now.weekday() >= 5:  # Weekend
        return False
    market_open = now.replace(hour=9, minute=15, second=0)
    market_close = now.replace(hour=15, minute=30, second=0)
    return market_open <= now <= market_close

def generate_alert_message(planets: Dict, aspects: List, market_data: Dict) -> str:
    """Generate formatted alert message with emojis"""
    lines = [
        "✨ <b>ASTRO TRADING ALERT</b> ✨",
        f"⏰ {get_current_ist().strftime('%Y-%m-%d %H:%M:%S %Z')}",
        "\n📊 <b>Market Data</b>"
    ]
    
    # Add market data
    for symbol, data in market_data.items():
        if data:
            change_emoji = "🟢" if data['change'] >= 0 else "🔴"
            lines.append(
                f"{symbol}: {data['price']} | "
                f"{change_emoji} {abs(data['change_pct']):.2f}%"
            )
    
    # Add planetary positions
    lines.extend(["\n🪐 <b>Planetary Positions</b>"])
    for planet, pos in planets.items():
        lines.append(f"{planet.ljust(8)}: {pos[0]:7.2f}°")
    
    # Add aspects
    if aspects:
        lines.extend(["\n🔮 <b>Active Aspects</b>"])
        for aspect in aspects:
            lines.extend([
                f"\n{aspect['aspect']['signal']}",
                f"│ {aspect['aspect']['from']} → {aspect['aspect']['to']} ({aspect['aspect']['angle']}°)",
                f"│ Current: {aspect['actual_angle']:.2f}° (Dev: {aspect['deviation']:.2f}°)",
                f"╰ Effective orb: {aspect['orb_used']:.2f}°"
            ])
    else:
        lines.append("\n🔍 No significant aspects found")
    
    # Add trading recommendations
    strong_signals = [a for a in aspects if a['deviation'] < 0.5]
    if strong_signals:
        lines.extend(["\n💡 <b>Trading Advice</b>"])
        if any("BULL" in a['aspect']['signal'] for a in strong_signals):
            lines.append("- Consider long positions")
        if any("BEAR" in a['aspect']['signal'] for a in strong_signals):
            lines.append("- Consider short positions")
        if any("TURNING POINT" in a['aspect']['signal'] for a in strong_signals):
            lines.append("- Market reversal likely")
    
    return "\n".join(lines)

# ===== MAIN EXECUTION =====
def main():
    swe.set_ephe_path(Config.EPHE_PATH)
    logger.info("Astro Trading Bot started")
    
    try:
        while True:
            try:
                current_time = get_current_ist()
                market_status = is_market_open()
                
                # Calculate Julian day for astronomical calculations
                jd = swe.julday(
                    current_time.year,
                    current_time.month,
                    current_time.day,
                    current_time.hour + current_time.minute/60
                )
                
                # Get planetary positions
                planet_positions = calculate_planet_positions(jd)
                if not planet_positions:
                    logger.warning("Failed to get planet positions")
                    time.sleep(Config.CHECK_INTERVAL)
                    continue
                
                # Detect aspects
                active_aspects = detect_aspects(planet_positions, market_status)
                
                # Get market data if market is open
                market_data = fetch_market_data() if market_status else {}
                
                # Generate and send alert if aspects found
                if active_aspects:
                    alert_message = generate_alert_message(
                        planet_positions,
                        active_aspects,
                        market_data
                    )
                    if not send_telegram_alert(alert_message):
                        logger.warning("Failed to send Telegram alert")
                
                # Sleep until next check
                sleep_time = Config.CHECK_INTERVAL - (time.time() % Config.CHECK_INTERVAL)
                time.sleep(sleep_time)
                
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                time.sleep(60)
                
    finally:
        logger.info("Bot shutdown complete")

if __name__ == "__main__":
    main()
