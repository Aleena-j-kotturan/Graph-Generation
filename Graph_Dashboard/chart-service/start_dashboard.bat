@echo off
REM Kill any existing nginx or streamlit if needed (optional cleanup)
REM taskkill /F /IM nginx.exe >nul 2>&1

REM Start nginx (optional if not already running)
start "" "C:\Users\aleena.j_simadvisory\Downloads\nginx\nginx-1.29.0\nginx-1.29.0\nginx.exe"

REM Wait 3 seconds to ensure nginx starts
timeout /t 3 >nul

REM Start Streamlit in background
start "" cmd /c "cd /d C:\Users\aleena.j_simadvisory\Documents\SIM_AI\GRAPH GENERATION_PR\Graph_Dashboard\chart-service && python -m streamlit run chart_app.py --server.port 8502 --server.headless true --server.baseUrlPath geni-dashboard-service"

REM Wait 5 seconds to allow Streamlit to boot
timeout /t 5 >nul

REM Open the HTTPS URL in the default browser
start https://localhost/geni-dashboard-service/?csv=data/test3.csv^&json=data/test3.json
