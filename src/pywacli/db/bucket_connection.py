import boto3
from botocore.exceptions import ClientError
from pywacli.cli.config_manager import load_config


def create_bucket_if_not_exists(s3_client, bucket_name):
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"✅ Bucket '{bucket_name}' already exists.")
        return True

    except ClientError as e:
        error_code = e.response["Error"]["Code"]

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


def _get_first_s3_entry():
    config = load_config()
    entries = config.get("media_storage", {}).get("entries", [])
    for entry in entries:
        if entry.get("provider") in ("s3", "r2", "b2"):
            return entry
    return None


def _normalize_endpoint(url):
    """Prepend https:// if no scheme is present."""
    if url and not url.startswith(("http://", "https://")):
        return f"https://{url}"
    return url


def conection_to_s3(entry=None):
    if entry is None:
        entry = _get_first_s3_entry()

    if entry is None:
        print("❌ No S3/R2/B2 storage entry found in config.")
        return None

    try:
        s3_client = boto3.client(
            "s3",
            endpoint_url=_normalize_endpoint(entry.get("endpoint")),
            aws_access_key_id=entry.get("access_key_id"),
            aws_secret_access_key=entry.get("secret_access_key"),
            region_name=entry.get("region", "us-east-1")
        )
        print("✅ Connected to S3 successfully")
        return s3_client

    except Exception as e:
        print(f"Error connecting to S3: {e}")
        return None
