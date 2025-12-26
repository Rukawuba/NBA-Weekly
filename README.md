# NBA Weekly Games Dashboard (Streamlit + BallDontLie)

A production-style Streamlit dashboard that pulls NBA game schedules for a selected week using the BallDontLie API, with caching, pagination handling, and CSV export.

## Demo
- Screenshots below 

## Features
- Week-based date defaults (Mon–Sun)
- Server-side caching (Streamlit `st.cache_data`)
- Resilient API requests (retries + rate-limit handling)
- Clean schedule table + CSV download

## Tech
- Python, Streamlit, Requests, Pandas
- BallDontLie API

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export BALLDONTLIE_API_KEY="YOUR_KEY"
streamlit run app.py
