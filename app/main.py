import asyncio
import os
from datetime import datetime

import boto3
from fastapi import FastAPI
from fastapi_utilities import repeat_every
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from app.api import data_fetch, prediction, main_backend
from app.core.logger import get_logger
from app.core.utils import update_data

logger = get_logger(__name__)

if os.getenv("ENV", "dev") != "prod":
    from dotenv import load_dotenv
    load_dotenv()

# Boto Client (Google Bucket)
boto_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv("BUCKET_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("BUCKET_SECRET_KEY"),
    endpoint_url='https://storage.googleapis.com'
)
    
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # Start background task
#     task = asyncio.create_task(data_fetch.fetch_data_loop(boto_client=boto_client))

#     yield  # App runs here

#     # Optional: cancel the background task on shutdown
#     task.cancel()
#     try:
#         await task
#     except asyncio.CancelledError:
#         pass

# Use a lock to prevent race conditions during the update
update_lock = asyncio.Lock()

app = FastAPI(title="Asset Price Prediction Backend")

@app.on_event("startup")
@repeat_every(seconds=60, wait_first=False, raise_exceptions=True) # Runs every minute
async def run_signal_generation():
    """
    This is the background task that updates data and generates signals.
    """
    async with update_lock:
        logger.info(f"[{datetime.utcnow().isoformat()}] Starting scheduled signal generation...")
        
        # 1. Update Data (This is synchronous, but we run it in a thread pool
        #    to avoid blocking the main async loop if it's I/O bound)
        #    If your update_data() is already async, 'await' it directly.
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, update_data)

# Register routers
# app.include_router(data_fetch.router)
app.include_router(prediction.router)
app.include_router(main_backend.router)