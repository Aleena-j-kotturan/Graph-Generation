import subprocess
import time
import webbrowser
import sys
import os

# Absolute path to your Streamlit app file
streamlit_app_path = os.path.abspath("chart_app.py")

# Start Streamlit with custom base path and headless mode
subprocess.Popen([
    sys.executable, "-m", "streamlit", "run", streamlit_app_path,
    "--server.headless", "true",
    "--server.baseUrlPath", "geni-dashboard-service",
    "--server.port", "8502"
])

# Wait for Streamlit to spin up
time.sleep(3)

# Open the custom URL in browser with query params
url = "https://localhost:8502/genai-dashboard-service/?csv=data/test3.csv&json=data/test3.json"
webbrowser.open(url)
