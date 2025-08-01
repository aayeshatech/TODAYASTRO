#!/usr/bin/env python3
import streamlit as st
import swisseph as swe
from datetime import datetime
import pytz
import logging
from typing import Dict, List, Tuple

# ===== BOT CONFIGURATION =====
class Config:
    EPHE_PATH = '/content/ephe'  # Adjusted for Colab
    ORB_REDUCTION_DURING_MARKET_HOURS = 0.3

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
                positions[name] = swe.calc_ut(jd, pid)[0][:2]
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

def is_market_open() -> bool:
    """Check if Indian stock market is open"""
    now = get_current_ist()
    if now.weekday() >= 5:
        return False
    market_open = now.replace(hour=9, minute=15, second=0)
    market_close = now.replace(hour=15, minute=30, second=0)
    return market_open <= now <= market_close

def generate_alert_message(planets: Dict, aspects: List) -> str:
    """Generate formatted alert message"""
    lines = [
        "✨ <b>ASTRO TRADING ALERT</b> ✨",
        f"⏰ {get_current_ist().strftime('%Y-%m-%d %H:%M:%S %Z')}",
        f"\n📊 <b>Market Status</b>: {'OPEN' if is_market_open() else 'CLOSED'}"
    ]
    
    lines.extend(["\n🪐 <b>Planetary Positions</b>"])
    for planet, pos in planets.items():
        lines.append(f"{planet.ljust(8)}: {pos[0]:7.2f}°")
    
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

def main():
    swe.set_ephe_path(Config.EPHE_PATH)
    st.title("Astro Trading Alerts")
    
    current_time = get_current_ist()
    market_status = is_market_open()
    jd = swe.julday(
        current_time.year,
        current_time.month,
        current_time.day,
        current_time.hour + current_time.minute/60
    )
    
    planet_positions = calculate_planet_positions(jd)
    if not planet_positions:
        st.error("Failed to calculate planet positions")
        return
    
    active_aspects = detect_aspects(planet_positions, market_status)
    alert_message = generate_alert_message(planet_positions, active_aspects)
    st.markdown(alert_message, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
