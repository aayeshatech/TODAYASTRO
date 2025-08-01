#!/usr/bin/env python3
"""
Astro Trading Alerts Bot - todayastro1.py
Monitors planetary aspects and sends trading alerts via Telegram
"""

import swisseph as swe
from datetime import datetime
import time
import pytz
import requests
import logging
import os
from typing import Dict, List, Optional, Tuple

# === Configuration ===
class Config:
    # Load from environment variables with fallback
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '7613703350:AAGIvRqgsG_yTcOlFADRSYd_FtoLOPwXDKk')
    CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '-1002840229810')
    EPHE_PATH = os.getenv('EPHEMERIS_PATH', '/usr/share/ephe')
    CHECK_INTERVAL = 60  # seconds
    ORB_REDUCTION_DURING_MARKET_HOURS = 0.3

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
PLANET_IDS = {
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
    # Format: {'from': planet, 'to': planet, 'angle': degrees, 'signal': name, 'orb': degrees}
    {'from': 'Jupiter', 'to': 'Sun', 'angle': 120, 'signal': 'STRONG BULLISH', 'orb': 1.5},
    {'from': 'Venus', 'to': 'Moon', 'angle': 0, 'signal': 'BULLISH', 'orb': 1.2},
    {'from': 'Saturn', 'to': 'Mars', 'angle': 90, 'signal': 'STRONG BEARISH', 'orb': 1.5},
    {'from': 'Rahu', 'to': 'Sun', 'angle': 180, 'signal': 'BEARISH', 'orb': 1.8},
    {'from': 'Mars', 'to': 'Mercury', 'angle': 90, 'signal': 'VOLATILE', 'orb': 1.5},
    {'from': 'Rahu', 'to': 'Ketu', 'angle': 180, 'signal': 'MARKET TURNING POINT', 'orb': 0.5}
]

# === Core Functions ===
def now_ist() -> datetime:
    """Get current IST time without microseconds"""
    return datetime.now(pytz.timezone('Asia/Kolkata')).replace(microsecond=0)

def get_planetary_positions(jd: float) -> Optional[Dict[str, List[float]]]:
    """Calculate current planetary positions"""
    positions = {}
    try:
        for name, pid in PLANET_IDS.items():
            if name == 'Ketu':
                rahu_pos = swe.calc_ut(jd, PLANET_IDS['Rahu'])[0][0]
                positions['Ketu'] = [(rahu_pos + 180) % 360, 0]
            else:
                positions[name] = swe.calc_ut(jd, pid)[0]
        return positions
    except Exception as e:
        logger.error(f"Planetary calculation error: {e}")
        return None

def check_aspects(planets: Dict[str, List[float]], market_open: bool) -> List[Dict]:
    """Check for active aspects with dynamic orbs"""
    active = []
    if not planets:
        return active

    for aspect in ASPECTS:
        try:
            p1, p2 = planets.get(aspect['from']), planets.get(aspect['to'])
            if None in (p1, p2):
                continue

            angle = abs((p1[0] - p2[0]) % 360)
            angle = min(angle, 360 - angle)
            orb = aspect['orb'] - (Config.ORB_REDUCTION_DURING_MARKET_HOURS if market_open else 0)
            
            if abs(angle - aspect['angle']) <= orb:
                active.append({
                    'aspect': aspect,
                    'actual': angle,
                    'deviation': abs(angle - aspect['angle']),
                    'orb_used': orb
                })
        except Exception as e:
            logger.error(f"Aspect check error: {e}")
    return active

def send_alert(message: str) -> bool:
    """Send Telegram alert with retry logic"""
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': Config.CHAT_ID,
        'text': message,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")
        return False

def is_market_open() -> bool:
    """Check if Indian market is open (Mon-Fri 9:15-15:30 IST)"""
    now = now_ist()
    if now.weekday() >= 5:  # Sat/Sun
        return False
    market_open = now.replace(hour=9, minute=15, second=0)
    market_close = now.replace(hour=15, minute=30, second=0)
    return market_open <= now <= market_close

def format_report(planets: Dict[str, List[float]], aspects: List[Dict]) -> str:
    """Generate formatted alert message"""
    lines = [
        "✨ <b>Astro Trading Alert</b> ✨",
        f"🕒 {now_ist().strftime('%Y-%m-%d %H:%M:%S %Z')}",
        "",
        "🪐 <b>Planetary Positions</b>"
    ]
    
    # Add planet positions
    lines.extend(f"{p.ljust(8)}: {pos[0]:7.2f}°" for p, pos in planets.items())
    
    # Add aspects
    lines.extend(["", "🔮 <b>Active Aspects</b>"])
    if aspects:
        for a in sorted(aspects, key=lambda x: x['deviation']):
            aspect = a['aspect']
            lines.extend([
                f"▫️ <b>{aspect['signal']}</b>",
                f"{aspect['from']} → {aspect['to']} ({aspect['angle']}°)",
                f"Angle: {a['actual']:.2f}° (Dev: {a['deviation']:.2f}°)",
                ""
            ])
    else:
        lines.append("No significant aspects")
    
    return "\n".join(lines)

# === Main Execution ===
def main():
    swe.set_ephe_path(Config.EPHE_PATH)
    logger.info("Astro Alerts Bot started")
    
    try:
        while True:
            try:
                current_time = now_ist()
                market_open = is_market_open()
                jd = swe.julday(current_time.year, current_time.month, 
                               current_time.day, current_time.hour + current_time.minute/60)
                
                if planets := get_planetary_positions(jd):
                    if aspects := check_aspects(planets, market_open):
                        report = format_report(planets, aspects)
                        if not send_alert(report):
                            logger.warning("Failed to send alert")
                
                # Sleep until next minute
                time.sleep(Config.CHECK_INTERVAL - time.time() % Config.CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                time.sleep(60)
    finally:
        logger.info("Bot shutdown complete")

if __name__ == "__main__":
    main()
