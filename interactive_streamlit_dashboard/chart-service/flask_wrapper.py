import subprocess
import sys

# File paths
streamlit_app_path = "chart_app.py"  # your Streamlit app
csv_file = "data/default.csv"
json_file = "data/default.json"

# Streamlit app URL parameters
subprocess.Popen([
    sys.executable, "-m", "streamlit", "run", streamlit_app_path,
    "--server.headless", "true", "--", f"--csv={csv_file}", f"--json={json_file}"
])
import subprocess
import time
import webbrowser
import sys

# Your Streamlit app file
streamlit_app_path = "chart_app.py"

# Your data files
csv_file = "data/default.csv"
json_file = "data/default.json"

# Start Streamlit in headless mode (no browser auto-launch)
subprocess.Popen([
    sys.executable, "-m", "streamlit", "run", streamlit_app_path,
    "--server.headless", "true"
])

# Optional: Wait a moment to allow Streamlit server to start
time.sleep(3)

# Open the Streamlit app with query parameters in browser
webbrowser.open(f"http://localhost:8502/?csv={csv_file}&json={json_file}")
