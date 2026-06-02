import os
import shutil


def store_media_local(file_path, dest_dir, entry=None):
    try:
        os.makedirs(dest_dir, exist_ok=True)
        dest_path = os.path.join(dest_dir, os.path.basename(file_path))
        shutil.copy2(file_path, dest_path)
        print(f"file {file_path} copied to local path {dest_path}")
        return True
    except Exception as e:
        print(f"Error copying file to local path: {e}")
        return False
