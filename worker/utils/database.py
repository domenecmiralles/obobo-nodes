import os
import boto3
import requests
from typing import List
from pymongo import MongoClient, ReturnDocument
from pymongo.synchronous.collection import Collection
from dotenv import load_dotenv

load_dotenv()


def get_s3_client():
    s3 = boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION"),
    )
    return s3



