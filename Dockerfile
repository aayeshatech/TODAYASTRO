import streamlit as st
import subprocess
from datetime import datetime

st.set_page_config(page_title="Astro Trading Dashboard", layout="wide")

def run_astro_bot():
    """Run the astro trading bot and capture output"""
    result = subprocess.run(
        ["python", "todayastro1.py"],
        capture_output=True,
        text=True
    )
    return result.stdout

# Dashboard UI
st.title("🌌 Astro Trading Bot Dashboard")
st.write(f"Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if st.button("🔄 Run Astro Analysis"):
    with st.spinner("Calculating planetary positions..."):
        output = run_astro_bot()
    
    st.subheader("Analysis Results")
    st.code(output)

    st.success("Analysis completed!")
