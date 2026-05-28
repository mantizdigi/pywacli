from src.db.bucket_connection import conection_to_s3, create_bucket_if_not_exists


_s3_clients = {}


def _get_s3_client(entry=None):
    key = id(entry) if entry else "default"
    if key not in _s3_clients:
        _s3_clients[key] = conection_to_s3(entry)
    return _s3_clients[key]


def upload_file_to_s3(file_path, object_name, bucket_name, entry=None):
    client = _get_s3_client(entry)
    if client is None:
        print("❌ No S3 client available. Cannot upload file.")
        return False

    if not create_bucket_if_not_exists(client, bucket_name):
        print(f"Failed to create or access bucket '{bucket_name}'. Cannot upload file.")
        return False

    try:
        client.upload_file(file_path, bucket_name, object_name)
        print(f"file {file_path} uploaded to s3 bucket {bucket_name} as {object_name}")
        return True
    except Exception as e:
        print(f"Error uploading file to S3: {e}")
        return False


def download_file_from_s3(file_path, object_name, bucket_name, entry=None):
    client = _get_s3_client(entry)
    if client is None:
        print("❌ No S3 client available. Cannot download file.")
        return False

    try:
        print(f"⬇ Downloading s3://{bucket_name}/{object_name} → {file_path}")
        client.download_file(bucket_name, object_name, file_path)
        print(f"file {object_name} downloaded from s3 bucket {bucket_name} to {file_path}")
        return True
    except Exception as e:
        print(f"Error downloading file from S3: {e}")
        return False
