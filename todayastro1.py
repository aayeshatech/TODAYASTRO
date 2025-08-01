import swisseph as swe
from datetime import datetime, timedelta
import time
import pytz
import requests
import logging
from typing import Dict, List, Optional

# === Configuration Section ===
class Config:
    BOT_TOKEN = '7613703350:AAGIvRqgsG_yTcOlFADRSYd_FtoLOPwXDKk'
    CHAT_ID = '-1002840229810'
    EPHE_PATH = '/usr/share/ephe'
    WATCHLIST_NAME = "EYE FUTURE WATCHLIST (2)"
    CHECK_INTERVAL = 60  # seconds
    ORB_REDUCTION_DURING_MARKET_HOURS = 0.3  # tighter orbs when market is open

# === Logging Setup ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('astro_alerts.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# === Astronomical Constants ===
DEFAULT_SYMBOLS = [
    "NSE:NIFTY50", "NSE:BANKNIFTY", "NSE:RELIANCE",
    "NSE:TATASTEEL", "NSE:HDFCBANK", "NSE:ICICIBANK",
    "NSE:INFY", "NSE:SBIN", "NSE:BAJFINANCE"
]

PLANET_IDS = {
    'Sun': swe.SUN,
    'Moon': swe.MOON,
    'Mercury': swe.MERCURY,
    'Venus': swe.VENUS,
    'Mars': swe.MARS,
    'Jupiter': swe.JUPITER,
    'Saturn': swe.SATURN,
    'Rahu': swe.MEAN_NODE,
    'Ketu': swe.MEAN_NODE  # Special handling for Ketu
}

ASPECTS = [
    # Bullish aspects
    {'from': 'Jupiter', 'to': 'Sun', 'angle': 120, 'signal': 'STRONG BULLISH', 'orb': 1.5},
    {'from': 'Venus', 'to': 'Moon', 'angle': 0, 'signal': 'BULLISH', 'orb': 1.2},
    {'from': 'Jupiter', 'to': 'Moon', 'angle': 120, 'signal': 'BULLISH', 'orb': 1.5},
    
    # Bearish aspects
    {'from': 'Saturn', 'to': 'Mars', 'angle': 90, 'signal': 'STRONG BEARISH', 'orb': 1.5},
    {'from': 'Rahu', 'to': 'Sun', 'angle': 180, 'signal': 'BEARISH', 'orb': 1.8},
    {'from': 'Saturn', 'to': 'Moon', 'angle': 90, 'signal': 'BEARISH', 'orb': 2.0},
    
    # Volatile aspects
    {'from': 'Mars', 'to': 'Mercury', 'angle': 90, 'signal': 'VOLATILE', 'orb': 1.5},
    {'from': 'Mars', 'to': 'Sun', 'angle': 90, 'signal': 'HIGH VOLATILITY', 'orb': 2.0},
    
    # Special aspects
    {'from': 'Rahu', 'to': 'Ketu', 'angle': 180, 'signal': 'MARKET TURNING POINT', 'orb': 0.5}
]

# === Core Functions ===
def now_ist() -> datetime:
    """Get current time in IST timezone with milliseconds removed"""
    return datetime.now(pytz.timezone('Asia/Kolkata')).replace(microsecond=0)

def get_planetary_positions(jd: float) -> Optional[Dict[str, List[float]]]:
    """Get current planetary positions with error handling"""
    planets = {}
    try:
        for name, planet_id in PLANET_IDS.items():
            if name == 'Ketu':
                # Ketu is always 180° from Rahu
                rahu_pos = swe.calc_ut(jd, PLANET_IDS['Rahu'])[0][0]
                planets['Ketu'] = [(rahu_pos + 180) % 360, 0, 0, 0, 0, 0]
            else:
                planets[name] = swe.calc_ut(jd, planet_id)[0]
        
        logger.debug(f"Planetary positions calculated at JD {jd}")
        return planets
    except Exception as e:
        logger.error(f"Error calculating planetary positions: {e}")
        return None

def check_aspects(planets: Dict[str, List[float]], market_open: bool) -> List[Dict]:
    """Check all configured aspects with adjustable orbs"""
    active_aspects = []
    if not planets:
        return active_aspects

    for aspect in ASPECTS:
        try:
            from_planet = planets.get(aspect['from'])
            to_planet = planets.get(aspect['to'])
            
            if None in (from_planet, to_planet):
                continue
                
            from_pos = from_planet[0]
            to_pos = to_planet[0]
            angle_diff = abs((from_pos - to_pos) % 360)
            angle_diff = min(angle_diff, 360 - angle_diff)
            
            # Adjust orb based on market hours
            current_orb = aspect['orb']
            if market_open:
                current_orb = max(0.5, current_orb - Config.ORB_REDUCTION_DURING_MARKET_HOURS)
            
            if abs(angle_diff - aspect['angle']) <= current_orb:
                active_aspects.append({
                    'aspect': aspect,
                    'actual_angle': angle_diff,
                    'deviation': abs(angle_diff - aspect['angle']),
                    'orb_used': current_orb
                })
                logger.info(f"Aspect activated: {aspect['from']} {aspect['angle']}° {aspect['to']} "
                          f"(Diff: {angle_diff:.2f}°, Orb: {current_orb:.2f}°)")
                
        except Exception as e:
            logger.error(f"Error checking aspect {aspect}: {e}")
            
    return active_aspects

def send_telegram_alert(message: str, max_retries: int = 3) -> bool:
    """Send alert to Telegram with retry logic"""
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': Config.CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.post(url, data=payload, timeout=10)
            response.raise_for_status()
            logger.info("Alert sent successfully")
            return True
        except requests.exceptions.RequestException as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
    
    logger.error(f"Failed to send alert after {max_retries} attempts")
    return False

def is_market_open() -> bool:
    """Check if Indian stock market is open with precise timing"""
    now = now_ist()
    weekday = now.weekday()
    
    # Market schedule
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    
    # Check if weekday (Monday=0 to Friday=4)
    if weekday >= 5:
        return False
        
    # Check if current time is within market hours
    return market_open <= now <= market_close

def generate_report(planets: Dict[str, List[float]], aspects: List[Dict]]) -> str:
    """Generate formatted report with planetary positions and aspects"""
    report = [
        "<b>🌌 Astro Trading Alert</b>",
        f"<i>{now_ist().strftime('%Y-%m-%d %H:%M:%S %Z')}</i>",
        "",
        "<b>🪐 Planetary Positions</b>"
    ]
    
    # Add planet positions
    for planet, pos in planets.items():
        report.append(f"{planet.ljust(8)}: {pos[0]:7.2f}°")
    
    # Add aspect information
    report.extend(["", "<b>🔮 Active Aspects</b>"])
    if not aspects:
        report.append("No significant aspects currently")
    else:
        for aspect in sorted(aspects, key=lambda x: x['deviation']):
            a = aspect['aspect']
            report.extend([
                f"✦ <b>{a['signal']}</b>",
                f"{a['from']} → {a['to']} ({a['angle']}°)",
                f"Angle: {aspect['actual_angle']:.2f}° (Dev: {aspect['deviation']:.2f}°, Orb: {aspect['orb_used']:.2f}°)",
                ""
            ])
    
    # Add watchlist
    report.extend([
        "",
        "<b>📈 Monitoring</b>",
        *[f"• {sym}" for sym in DEFAULT_SYMBOLS]
    ])
    
    return "\n".join(report)

def initialize_ephemeris():
    """Initialize Swiss Ephemeris with error handling"""
    try:
        swe.set_ephe_path(Config.EPHE_PATH)
        logger.info(f"Ephemeris initialized at {Config.EPHE_PATH}")
    except Exception as e:
        logger.error(f"Ephemeris initialization failed: {e}")
        raise

# === Main Execution ===
def main():
    """Main execution loop"""
    initialize_ephemeris()
    logger.info("Astro Trading Alerts Bot started")
    
    try:
        while True:
            try:
                current_time = now_ist()
                market_status = is_market_open()
                
                # Calculate Julian Day
                jd = swe.julday(current_time.year, current_time.month, current_time.day,
                              current_time.hour + current_time.minute/60 + current_time.second/3600)
                
                # Get planetary data
                planets = get_planetary_positions(jd)
                if planets:
                    # Check aspects with market status
                    aspects = check_aspects(planets, market_status)
                    
                    if aspects:
                        report = generate_report(planets, aspects)
                        send_telegram_alert(report)
                
                # Calculate sleep time until next minute
                sleep_time = Config.CHECK_INTERVAL - (time.time() % Config.CHECK_INTERVAL)
                time.sleep(sleep_time)
                
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                time.sleep(60)
                
    finally:
        logger.info("Bot shutdown complete")

if __name__ == "__main__":
    main()
