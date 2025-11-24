import asyncio
import random

from app.core.logger import get_logger

logger = get_logger(__name__)

# Data Fetcher Initialization
active_tasks = set()  # Collect all current active fetching task
found_data_event = asyncio.Event()  # Declare event if data found, to stop doing fetching
task_counter = 0  # Task counter, declare globally for reset after data found

async def actual_fetch(task_id):
    # Check if data currently found, if not do the fetching, if found, skip
    if found_data_event.is_set():
        return

    logger.info(f"[Task {task_id}] Checking for data...")

    # Random < 0.8 happens when data not found, else it found so begin storing the data
    if random.random() < 0.8:
        await asyncio.sleep(random.randint(3, 4))  # Simulate fetching
        logger.info(f"[Task {task_id}] No data found, skipping...")
        return

    # When data found, set the event so incoming fetch will skipped
    logger.info(f"[Task {task_id}] Found data, cancelling other tasks...")
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
        await asyncio.sleep(random.randint(4, 8))  # Simulate storing fetched data
        logger.info(f"[Task {task_id}] Finished storing fetching data.")
    except asyncio.CancelledError:  # The other task that cancelled
        logger.info(f"[Task {task_id}] Cancelled during fetch.")
    finally:
        found_data_event.clear()
        global task_counter
        task_counter = 0  # ✅ Reset counter after successful fetch

async def fetch_data_loop():
    global task_counter  # Define global to get the variable
    while True:  # Looping
        if not found_data_event.is_set():  # If data not found
            # Create task with id task_counter
            task = asyncio.create_task(actual_fetch(task_counter), name=f"fetch-task-{task_counter}")
            active_tasks.add(task)  # Add to the active_tasks set

            # Define function to discard task from active_tasks set after finished
            def done_callback(t):
                active_tasks.discard(t)

            task.add_done_callback(done_callback)  # Attach the discard function
            task_counter += 1  # Counter += 1 for the next task

        await asyncio.sleep(1)  # Delay one second per loop