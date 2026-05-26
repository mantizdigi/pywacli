from db.bucket_connection import conection_to_s3 ,create_bucket_if_not_exists

s3_client = conection_to_s3()

def upload_file_to_s3(file_path, object_name, bucket_name):
    if not create_bucket_if_not_exists(s3_client,bucket_name):
        print(f"Failed to create or access bucket '{bucket_name}'. Cannot upload file.")
        return
    
    try:
        s3_client.upload_file(file_path,bucket_name,object_name)
        print(f"file {file_path} uploaded to s3 bucket {bucket_name} as {object_name}")
        return True
    except Exception as e:
        print(f"Error uploading file to S3: {e}")


def download_file_from_s3(file_path, object_name, bucket_name):

    if not create_bucket_if_not_exists(s3_client,bucket_name):
        print(f"Failed to create or access bucket '{bucket_name}'. Cannot download file.")
        return
    
    try:
        s3_client.download_file(file_path,bucket_name,object_name)
        print(f"file {object_name} downloaded from s3 bucket {bucket_name} to {file_path}")
        return True
    except Exception as e:
        print(f"Error downloading file from S3: {e}")

