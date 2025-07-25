@echo off

REM Kill old nginx
taskkill /F /IM nginx.exe >nul 2>&1

REM Start nginx
start "" "C:\Users\aleena.j_simadvisory\Downloads\nginx\nginx-1.29.0\nginx-1.29.0\nginx.exe"
timeout /t 3 >nul

REM Start Streamlit
start "" cmd /c "cd /d C:\Users\aleena.j_simadvisory\Documents\SIM_AI\GRAPH GENERATION_PR\Graph_Dashboard\chart-service && python -m streamlit run chart_app.py --server.port 8502 --server.headless true --server.baseUrlPath geni-dashboard-service"
timeout /t 5 >nul

REM Open HTTPS version in browser
start "" "https://localhost/geni-dashboard-service/?csv=data/test3.csv&json=data/test3.json"
