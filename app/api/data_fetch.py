# Fetch data from Coindesk for TAO-USD
# - Check if there is existing data in bucket
# - If there isn't, fetch all data available for hourly, daily, and weekly
# - If there is existing data, find out latest known data and fetch the remaining
# - Doesn't support partially missing data (in the middle of data)
# - Start fetching every 0.5 second from target_ts - 1 timestamp seconds

import asyncio
import functools
import random
import time
# import ntplib
from time import ctime

import boto3

from app.core.logger import get_logger
from app.core.config import FETCH_TS_RANGE_START, FETCH_TS_RANGE_END
from app.services.price_fetcher import (
    is_asset_price_updated,
    stored_asset_price_first_time,
    update_asset_price
)

logger = get_logger(__name__)

# client = ntplib.NTPClient()
# response = client.request('pool.ntp.org')

# Data Fetcher Initialization
active_tasks = set()  # Collect all current active fetching task
found_data_event = asyncio.Event()  # Declare event if data found, to stop doing fetching
task_counter = 0  # Task counter, declare globally for reset after data found

async def actual_fetch(boto_client: boto3, task_id: int):
    # Check if data currently found, if not do the fetching, if found, skip
    if found_data_event.is_set():
        return

    logger.info(f"[Task {task_id}] Checking for data...")

    # Random < 0.8 happens when data not found, else it found so begin storing the data
    loop = asyncio.get_running_loop()
    is_updated, update_code = await loop.run_in_executor(
        None,
        functools.partial(is_asset_price_updated, boto_client=boto_client, asset_code="cadli-tao-usd")
    )
    
    # Check if any error happen
    if update_code == "error": return
    
    if is_updated or update_code == "updated":
        # await asyncio.sleep(random.randint(3, 4))  # Simulate fetching
        logger.info(f"[Task {task_id}] Data is up to date, skipping...")
        return

    # When data found, set the event so incoming fetch will skipped
    logger.info(f"[Task {task_id}] is not updated, cancelling other tasks...")
    found_data_event.set()

    # For the currently working fetch, cancel the task
    for task in list(active_tasks):  # Loop to all the active tasks
        # Check if task is not this found task, to prevent getting cancelled too
        if not task.get_name().endswith(str(task_id)):
            task.cancel()  # Cancel other tasks
            
    # Wait for all the tasks cancelled
    await asyncio.gather(
        *[t for t in active_tasks if not t.get_name().endswith(str(task_id))],
        return_exceptions=True
    )
    active_tasks.clear()  # Clear the set to empty


    # Begin storing the fetched data
    try:
        if update_code == "not_exist":
            logger.info(f"[Task {task_id}] Begin fetch for the first time...")
            stored_asset_price_first_time(boto_client=boto_client)
        elif update_code == "not_updated":
            logger.info(f"[Task {task_id}] Begin updating the data...")
            update_asset_price(boto_client=boto_client)
            # await asyncio.sleep(random.randint(4, 8))  # Simulate updating the data
        else:
            logger.error(f"[Task {task_id}] Unknown Task, is_updated: {is_updated}, update_code: {update_code}")
            
        # await asyncio.sleep(random.randint(4, 8))  # Simulate storing fetched data
        logger.info(f"[Task {task_id}] Finished storing fetched data.")
    except asyncio.CancelledError:  # The other task that cancelled
        logger.info(f"[Task {task_id}] Cancelled during fetch.")
    finally:
        found_data_event.clear()
        global task_counter
        task_counter = 0  # ✅ Reset counter after successful fetch

async def fetch_data_loop(boto_client: boto3):
    first_time = True  # Always do the task once for the first time
    
    global task_counter  # Define global to get the variable
    while True:  # Looping
        if not first_time:
            current_ts = int(time.time())  # x = 1754744400 - 30, ftre = 60 seconds
            # Calculate the next hourly timestamp
            next_hourly_ts = (((current_ts - FETCH_TS_RANGE_END) // 3600) + 1) * 3600  # ((1754744370 // 3600) + 1) * 3600 = 1754744400

            # Define the 5-minute range before the next hourly timestamp
            skip_range_start = next_hourly_ts - FETCH_TS_RANGE_START # 5 minutes = 300 seconds 
            skip_range_end = next_hourly_ts + FETCH_TS_RANGE_END
            in_range = skip_range_start <= current_ts < skip_range_end
            if not in_range:
                # Skip this iteration
                logger.info(f"Current TS: {current_ts}, task will active within {skip_range_start} to {skip_range_end}")
            
                await asyncio.sleep(1)
                continue
        
        if not found_data_event.is_set():  # If data not found
            # Create task with id task_counter
            task = asyncio.create_task(actual_fetch(boto_client=boto_client, task_id=task_counter), name=f"fetch-task-{task_counter}")
            active_tasks.add(task)  # Add to the active_tasks set

            # Define function to discard task from active_tasks set after finished
            def done_callback(t):
                active_tasks.discard(t)

            task.add_done_callback(done_callback)  # Attach the discard function
            task_counter += 1  # Counter += 1 for the next task

        first_time = False
        
        await asyncio.sleep(1)  # Delay one second per loop