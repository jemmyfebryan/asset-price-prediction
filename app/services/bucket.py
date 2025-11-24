import json
from io import BytesIO

import boto3
import botocore.exceptions
import pandas as pd

from app.core.logger import get_logger
from app.core.bucket import BUCKET_NAME, MAIN_DIR, ASSET_PRICE_DIR

logger = get_logger(__name__)

def is_file_exist(boto_client: boto3, bucket_name: str, key: str) -> bool:
    """
    Check if a file exists in the specified S3 bucket.
    """

    try:
        boto_client.head_object(Bucket=bucket_name, Key=key)
        logger.info(f"File: {key} does exist in Bucket: {bucket_name}")
        return True
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            logger.info(f"File {key} does not exist in Bucket: {bucket_name}!")
            return False
        else:
            logger.error(f"Error when checking file: {key} in Bucket: {bucket_name}: {str(e)}")
            return False
        
def get_asset_price_from_bucket(boto_client: boto3.client, asset_code: str = "cadli-tao-usd") -> pd.DataFrame:
    """
    Load and return CSV content from S3 as a pandas DataFrame.
    Returns empty DataFrame if the file does not exist or fails to load.
    """
    try:
        key = f"{MAIN_DIR}/{ASSET_PRICE_DIR}/{asset_code}.csv"
        bucket_name = BUCKET_NAME

        response = boto_client.get_object(Bucket=bucket_name, Key=key)
        content = response['Body'].read()
        df = pd.read_csv(BytesIO(content))

        logger.info(f"{asset_code}.csv loaded from bucket!")
        return df
    except Exception as e:
        logger.error(f"Error when loading {asset_code}.csv from bucket: {str(e)}")
        return pd.DataFrame()  # Return empty DataFrame on failure


def save_asset_price_to_bucket(boto_client: boto3.client, asset_code: str, df: pd.DataFrame) -> None:
    """
    Save a pandas DataFrame to S3 as a CSV file.
    """
    try:
        key = f"{MAIN_DIR}/{ASSET_PRICE_DIR}/{asset_code}.csv"
        bucket_name = BUCKET_NAME

        csv_buffer = BytesIO()
        df.to_csv(csv_buffer, index=False)

        boto_client.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=csv_buffer.getvalue(),
            ContentType='text/csv'
        )

        logger.info(f"{asset_code}.csv stored to bucket!")
    except Exception as e:
        logger.error(f"Error when saving {asset_code}.csv to bucket: {str(e)}")