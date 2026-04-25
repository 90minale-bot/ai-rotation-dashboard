@echo off
cd /d C:\Users\90min\test_final\initial-stock-project-working

call venv\Scripts\activate

streamlit run ai_roi_tracker\roi_dashboard.py

pause