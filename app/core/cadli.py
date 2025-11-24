import requests
import time
import json
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from tqdm import tqdm
from typing import Dict, List, Literal

from app.core.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Constants
BASE_URL = 'https://data-api.coindesk.com/index/cc/v1/historical/'  # add interval 'hours' or 'daily'
MARKET = 'cadli'
INSTRUMENT = 'TAO-USD'
AGGREGATE = 1
# LIMIT = 2000

def _interval_to_url(interval: str) -> str:
    url_mapping = {
        "minutely": "minutes",
        "hourly": "hours",
        "daily": "days",
        "weekly": "weeks"
    }
    
    url_result = url_mapping.get(interval, None)
    if url_result == None:
        logger.warning(f"Interval should be in ['minutely', 'hourly', 'daily', 'weekly']. Got {interval} instead.")
        return ""
    
    return url_result

def _align_and_aggregate_weekly(daily_data: List[Dict], n_weeks: int) -> List[Dict]:
    weekly_buckets = defaultdict(list)

    for day in daily_data:
        dt = datetime.utcfromtimestamp(day['TIMESTAMP']).replace(tzinfo=timezone.utc)
        week_start = dt - timedelta(days=dt.weekday())  # Monday as week start
        week_key = int(week_start.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
        weekly_buckets[week_key].append(day)

    sorted_weeks = sorted(weekly_buckets.items(), reverse=True)[:n_weeks]
    aggregated_weeks = []

    for week_key, week_chunk in sorted_weeks:
        aggregated_weeks.append(_aggregate_week_chunk(week_chunk, week_key))

    return aggregated_weeks[::-1]  # Return oldest first

def _aggregate_week_chunk(week_chunk: List[Dict], week_key: int) -> Dict:
    week_chunk_sorted = sorted(week_chunk, key=lambda x: x['TIMESTAMP'])

    return {
        'UNIT': 'WEEK',
        'TIMESTAMP': week_key,
        'TYPE': week_chunk_sorted[0]['TYPE'],
        'MARKET': week_chunk_sorted[0]['MARKET'],
        'INSTRUMENT': week_chunk_sorted[0]['INSTRUMENT'],
        'OPEN': week_chunk_sorted[0]['OPEN'],
        'HIGH': max(day['HIGH'] for day in week_chunk),
        'LOW': min(day['LOW'] for day in week_chunk),
        'CLOSE': week_chunk_sorted[-1]['CLOSE'],
        'FIRST_MESSAGE_TIMESTAMP': week_chunk_sorted[0]['FIRST_MESSAGE_TIMESTAMP'],
        'LAST_MESSAGE_TIMESTAMP': week_chunk_sorted[-1]['LAST_MESSAGE_TIMESTAMP'],
        'FIRST_MESSAGE_VALUE': week_chunk_sorted[0]['FIRST_MESSAGE_VALUE'],
        'HIGH_MESSAGE_VALUE': max(day['HIGH_MESSAGE_VALUE'] for day in week_chunk),
        'HIGH_MESSAGE_TIMESTAMP': max(week_chunk, key=lambda d: d['HIGH_MESSAGE_VALUE'])['HIGH_MESSAGE_TIMESTAMP'],
        'LOW_MESSAGE_VALUE': min(day['LOW_MESSAGE_VALUE'] for day in week_chunk),
        'LOW_MESSAGE_TIMESTAMP': min(week_chunk, key=lambda d: d['LOW_MESSAGE_VALUE'])['LOW_MESSAGE_TIMESTAMP'],
        'LAST_MESSAGE_VALUE': week_chunk_sorted[-1]['LAST_MESSAGE_VALUE'],
        'TOTAL_INDEX_UPDATES': sum(day['TOTAL_INDEX_UPDATES'] for day in week_chunk),
        'VOLUME': sum(day['VOLUME'] for day in week_chunk),
        'QUOTE_VOLUME': sum(day['QUOTE_VOLUME'] for day in week_chunk),
        'VOLUME_TOP_TIER': sum(day['VOLUME_TOP_TIER'] for day in week_chunk),
        'QUOTE_VOLUME_TOP_TIER': sum(day['QUOTE_VOLUME_TOP_TIER'] for day in week_chunk),
        'VOLUME_DIRECT': sum(day['VOLUME_DIRECT'] for day in week_chunk),
        'QUOTE_VOLUME_DIRECT': sum(day['QUOTE_VOLUME_DIRECT'] for day in week_chunk),
        'VOLUME_TOP_TIER_DIRECT': sum(day['VOLUME_TOP_TIER_DIRECT'] for day in week_chunk),
        'QUOTE_VOLUME_TOP_TIER_DIRECT': sum(day['QUOTE_VOLUME_TOP_TIER_DIRECT'] for day in week_chunk),
    }

def get_last_n_data(n: int, interval: Literal["hourly", "daily", "weekly"]) -> Dict:
    try:
        to_ts = int(time.time()) // 3600 * 3600

        if interval == "weekly":
            # Fetch extra days to ensure full weeks
            daily_limit = n * 7 + 14  # Extra 2 weeks buffer
            daily_data = get_last_n_data(daily_limit, "daily").get("Data", [])
            weekly_data = _align_and_aggregate_weekly(daily_data, n)
            return {"Data": weekly_data, "Err": {}}

        params = {
            "market": MARKET,
            "instrument": INSTRUMENT,
            "limit": n,
            "aggregate": AGGREGATE,
            "fill": "true",
            "apply_mapping": "true",
            "response_format": "JSON",
            "to_ts": to_ts,
        }

        request_url = BASE_URL + _interval_to_url(interval=interval)
        response = requests.get(request_url, params=params, headers={"Content-type": "application/json; charset=UTF-8"})
        return response.json()

    except Exception as e:
        logger.error(f"Error when fetch CADLI: {str(e)}")
        return {}
    
    
    
# Fetching Data for First Time
def get_all_cadli(interval: Literal["hourly", "daily", "weekly"]):
    # Constants
    LIMIT = 2000
    to_ts = int(time.time()) // 3600 * 3600

    all_data = []
    base_json_data = None

    with tqdm(desc="Fetching CADLI data (backward)") as pbar:
        while True:
            params = {
                "market": MARKET,
                "instrument": INSTRUMENT,
                "limit": LIMIT,
                "aggregate": AGGREGATE,
                "fill": "true",
                "apply_mapping": "true",
                "response_format": "JSON",
                "to_ts": to_ts,
            }

            request_url = BASE_URL + _interval_to_url(interval=interval)
            response = requests.get(request_url, params=params, headers={"Content-type": "application/json; charset=UTF-8"})

            try:
                json_data = response.json()
            except ValueError:
                print("❌ Failed to parse JSON response.")
                break

            data = json_data.get("Data", [])
            if not data:
                print("✅ Reached beginning of data (no more data returned).")
                break

            if base_json_data is None:
                base_json_data = json_data.copy()
                base_json_data["Data"] = []

            all_data.extend(data)
            to_ts = min(d["TIMESTAMP"] for d in data) - 3600
            pbar.update(len(data))

    if base_json_data is not None:
        base_json_data["Data"] = all_data
        return base_json_data
    else:
        return {"Data": []}  # fallback if no data was ever fetched

def get_cadli_from(from_ts: int, interval: Literal["hourly", "daily", "weekly"]):
    STEP = {
        "hourly": 3600,
        "daily": 86400,
        "weekly": 604800,
    }[interval]

    current_ts = int(time.time()) // STEP * STEP
    to_ts = from_ts
    all_data = []
    base_json_data = None

    with tqdm(desc="Fetching CADLI data (forward)") as pbar:
        while to_ts < current_ts:
            remaining_steps = (current_ts - to_ts) // STEP
            limit = min(2000, remaining_steps)

            params = {
                "market": MARKET,
                "instrument": INSTRUMENT,
                "limit": limit,
                "aggregate": AGGREGATE,
                "fill": "true",
                "apply_mapping": "true",
                "response_format": "JSON",
                "to_ts": to_ts + limit * STEP,
            }

            request_url = BASE_URL + _interval_to_url(interval=interval)
            response = requests.get(request_url, params=params, headers={"Content-type": "application/json; charset=UTF-8"})

            try:
                json_data = response.json()
            except ValueError:
                print("❌ Failed to parse JSON response.")
                break

            data = json_data.get("Data", [])
            if not data:
                print("✅ No more data returned.")
                break

            if base_json_data is None:
                base_json_data = json_data.copy()
                base_json_data["Data"] = []

            all_data.extend(data)

            latest_ts = max(d["TIMESTAMP"] for d in data)
            if latest_ts <= to_ts:
                print("⚠️ No forward progress in data, exiting to avoid infinite loop.")
                break

            to_ts = latest_ts + STEP
            pbar.update(len(data))

    if base_json_data is not None:
        base_json_data["Data"] = all_data
        return base_json_data
    else:
        return {"Data": []}
