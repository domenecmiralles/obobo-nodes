import os
import boto3
import requests
from typing import List, Optional
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

def get_s3_client() -> Optional[boto3.client]:
    """Get S3 client for file uploads"""
    try:
        # Try to get from environment variables first
        access_key = os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        region = os.getenv("AWS_REGION", "us-east-1")
        
        if not access_key or not secret_key:
            logger.warning("AWS credentials not found in environment variables")
            return None
        
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )
        
        logger.info("Successfully created S3 client")
        return s3_client
        
    except Exception as e:
        logger.error(f"Failed to create S3 client: {e}")
        return None



