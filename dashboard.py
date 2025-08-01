import streamlit as st
import subprocess

st.title("Astro Trading Bot Monitor")

if st.button("Run Bot"):
    with st.spinner("Running astro analysis..."):
        result = subprocess.run(
            ["python", "todayastro1.py"],
            capture_output=True,
            text=True
        )
        st.code(result.stdout)
