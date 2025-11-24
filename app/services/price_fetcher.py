import time
import json
from io import BytesIO
from typing import Dict, List, Tuple, Literal

import boto3
import requests
import pandas as pd

from app.services.bucket import (
    is_file_exist,
    get_asset_price_from_bucket,
    save_asset_price_to_bucket
)
from app.core.cadli import get_last_n_data, get_all_cadli, get_cadli_from
from app.core.bucket import BUCKET_NAME, MAIN_DIR, ASSET_PRICE_DIR
from app.core.logger import get_logger

logger = get_logger(__name__)

# # CADLI Constants
# BASE_URL = 'https://data-api.coindesk.com/index/cc/v1/historical/'
# MARKET = 'cadli'
# INSTRUMENT = 'TAO-USD'
# LIMIT = 2000
# AGGREGATE = 1

def is_asset_price_updated(boto_client: boto3, asset_code: str = "cadli-tao-usd") -> Tuple[bool, Literal["updated", "not_exist", "not_updated", "error"]]:
    try:
        # Check if asset price in bucket is updated or not
        ## Check latest hourly timestamp from Coindesk
        last_data: Dict[str, List[Dict]] = get_last_n_data(n=1, interval="hourly")
        latest_hourly_ts_coindesk = last_data["Data"][0].get("TIMESTAMP")
        
        logger.info(f"Latest hourly Timestamp on Coindesk: {latest_hourly_ts_coindesk}")
        
        ## Check latest hourly timestamp from Bucket
        if is_asset_price_exist(boto_client=boto_client):  # Exist?
            df_asset_price = get_asset_price_from_bucket(
                boto_client=boto_client,
                asset_code=asset_code
            )
            try:
                # latest_hourly_ts_bucket = max([val.get("TIMESTAMP") for val in asset_price["Data"]])
                latest_hourly_ts_bucket = int(df_asset_price["TIMESTAMP"].max())
                logger.info(f"Latest hourly Timestamp on Bucket: {latest_hourly_ts_bucket}")
            except Exception as e:
                logger.error(f"Error when fetch price during check is updated: {str(e)}")
        else:  # If not exist, return False, meaning asset price is not updated
            return False, "not_exist"
        
        ## Check if Hourly Timestamp updated
        if latest_hourly_ts_coindesk == latest_hourly_ts_bucket:
            return True, "updated"
        return False, "not_updated"
    except Exception as e:
        logger.error(f"Error when checking if price updated: {str(e)}")
        return False, "error"
        

def is_asset_price_exist(boto_client: boto3, asset_code: str = "cadli-tao-usd") -> bool:
    """
    Check if a file exists in the specified S3 bucket.
    """
    key = f"{MAIN_DIR}/{ASSET_PRICE_DIR}/{asset_code}.csv"
    bucket_name = BUCKET_NAME
    
    is_exist = is_file_exist(
        boto_client=boto_client,
        bucket_name=bucket_name,
        key=key
    )
    
    return is_exist

def stored_asset_price_first_time(boto_client: boto3, asset_code: str = "cadli-tao-usd"):
    try:
        all_data_hourly = get_all_cadli(interval="hourly")
        
        # Get important columns
        df = pd.DataFrame(all_data_hourly['Data'])[['TIMESTAMP', 'OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLUME']]
        df.drop_duplicates(inplace=True)
        df.sort_values(by="TIMESTAMP", inplace=True)
        
        save_asset_price_to_bucket(boto_client=boto_client, asset_code=asset_code, df=df)
        logger.info(f"Finish stored asset price for the first time!")
    except Exception as e:
        logger.error(f"Error when stored asset price for the first time: {str(e)}")

def update_asset_price(boto_client: boto3, asset_code: str = "cadli-tao-usd"):
    # Get the latest timestamp
    df_asset_price = get_asset_price_from_bucket(
        boto_client=boto_client,
        asset_code=asset_code
    )
    try:
        # latest_hourly_ts_bucket = max([val.get("TIMESTAMP") for val in asset_price["Data"]])
        latest_hourly_ts_bucket = int(df_asset_price["TIMESTAMP"].max())
        logger.info(f"Latest hourly Timestamp on Bucket: {latest_hourly_ts_bucket}")
        
        # Get remaining data
        remaining_data_hourly = get_cadli_from(
            from_ts=latest_hourly_ts_bucket,
            interval="hourly"
        )
        remaining_df = pd.DataFrame(remaining_data_hourly['Data'])[['TIMESTAMP', 'OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLUME']]
        
        # Concat data
        updated_df = pd.concat([df_asset_price, remaining_df], axis=0)
        # Remove duplicate data if any
        updated_df.drop_duplicates(inplace=True)
        # Sort data
        updated_df.sort_values(by="TIMESTAMP", inplace=True)
        
        # Save data
        save_asset_price_to_bucket(boto_client=boto_client, asset_code=asset_code, df=updated_df)
        logger.info(f"Finish update asset price from_ts: {latest_hourly_ts_bucket} to current timestamp!")
    except Exception as e:
        logger.error(f"Error when fetch price during updating asset price {str(e)}")
    