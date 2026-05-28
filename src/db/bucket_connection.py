from dotenv import load_dotenv
import os
import boto3

load_dotenv()

S3_ENDPOINT = os.getenv("S3_ENDPOINT")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
REGION_NAME = os.getenv("REGION_NAME")
BUCKET_NAME = os.getenv("BUCKET_NAME")

from botocore.exceptions import ClientError

def create_bucket_if_not_exists(s3_client, bucket_name):
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"✅ Bucket '{bucket_name}' already exists.")
        return True

    except ClientError as e:
        error_code = e.response["Error"]["Code"]

        # Bucket does not exist
        if error_code in ["404", "NoSuchBucket"]:
            try:
                s3_client.create_bucket(Bucket=bucket_name)
                print(f"✅ Bucket '{bucket_name}' created successfully.")
                return True

            except Exception as create_error:
                print(f"❌ Error creating bucket: {create_error}")
                return False

        else:
            print(f"❌ Bucket check error: {e}")
            return False
        
        
def conection_to_s3():
    try:
        
        s3_client = boto3.client(
            "s3",
            endpoint_url=S3_ENDPOINT,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name = REGION_NAME
        )
        print("✅ Connected to S3 successfully")
        return s3_client
    
    except Exception as e:
        print(f"Error connecting to S3: {e}")
        return None