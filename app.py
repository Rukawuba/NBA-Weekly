import os
import time
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st


API_BASE = "https://api.balldontlie.io"
TZ = ZoneInfo("Europe/Madrid")


def week_bounds(d: date) -> tuple[date, date]:
    monday = d - timedelta(days=d.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def bdl_headers() -> dict:
    api_key = os.getenv("BALLDONTLIE_API_KEY") or os.getenv("BALDONTLIE_API_KEY")
    if not api_key:
        st.error("Missing API key. Set BALLDONTLIE_API_KEY and restart Streamlit.")
        st.stop()
    return {"Authorization": api_key}


def safe_get(url: str, params: dict, headers: dict, timeout=20, retries=4, backoff=1.8):
    last_err = None
    for i in range(retries):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=timeout)
            if r.status_code == 429:
                time.sleep(backoff ** i)
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last_err = e
            time.sleep(backoff ** i)
    raise RuntimeError(f"Request failed after {retries} tries: {last_err}")


@st.cache_data(ttl=60 * 10)  # 10 min
def fetch_games(start_date: date, end_date: date, per_page: int = 100) -> pd.DataFrame:
    url = f"{API_BASE}/v1/games"
    headers = bdl_headers()

    cursor = 0
    rows = []

    while True:
        params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "per_page": per_page,
            "cursor": cursor,
        }
        payload = safe_get(url, params=params, headers=headers)
        rows.extend(payload.get("data", []))
        meta = payload.get("meta", {}) or {}

        next_cursor = meta.get("next_cursor")
        if next_cursor is None:
            break
        cursor = next_cursor

    if not rows:
        return pd.DataFrame()

    df = pd.json_normalize(rows)

    # Convert tipoff time to local timezone if present
    if "datetime" in df.columns:
        dt_utc = pd.to_datetime(df["datetime"], errors="coerce", utc=True)
        df["tipoff_local"] = dt_utc.dt.tz_convert(TZ).dt.strftime("%Y-%m-%d %H:%M")
    else:
        df["tipoff_local"] = None

    df["matchup"] = (
        df.get("visitor_team.full_name", "").fillna("")
        + " @ "
        + df.get("home_team.full_name", "").fillna("")
    )

    keep = [
        "id",
        "date",
        "tipoff_local",
        "status",
        "postseason",
        "visitor_team.abbreviation",
        "visitor_team_score",
        "home_team.abbreviation",
        "home_team_score",
        "matchup",
    ]
    df = df[[c for c in keep if c in df.columns]].copy()

    # Sort by date then local tipoff if available
    sort_cols = ["date"] + (["tipoff_local"] if "tipoff_local" in df.columns else [])
    df = df.sort_values(sort_cols, ascending=True)

    return df


st.set_page_config(page_title="NBA Games This Week", layout="wide")

today_local = datetime.now(TZ).date()
default_start, default_end = week_bounds(today_local)

st.title("🏀 NBA Games — This Week (BallDontLie)")
st.caption(f"Timezone: Europe/Madrid | Today: {today_local.isoformat()}")

with st.sidebar:
    st.header("Filters")
    start = st.date_input("Start date", value=default_start)
    end = st.date_input("End date", value=default_end)

    show_only_live = st.checkbox("Only live / in-progress", value=False)
    show_only_final = st.checkbox("Only finals", value=False)

if start > end:
    st.error("Start date must be <= End date.")
    st.stop()

df = fetch_games(start, end)

if df.empty:
    st.warning("No games returned for this date range.")
    st.stop()

# Status filters (basic, but works)
if show_only_live:
    df = df[df["status"].astype(str).str.contains("Qtr|Half", case=False, na=False)]
if show_only_final:
    df = df[df["status"].astype(str).str.contains("Final", case=False, na=False)]

c1, c2 = st.columns(2)
c1.metric("Games", len(df))
c2.metric("Range", f"{start.isoformat()} → {end.isoformat()}")

st.subheader("Schedule")
st.dataframe(df, use_container_width=True, hide_index=True)

st.download_button(
    "Download CSV",
    df.to_csv(index=False).encode("utf-8"),
    file_name=f"nba_games_{start.isoformat()}_{end.isoformat()}.csv",
    mime="text/csv",
)
