import os
import sys
import subprocess
from decouple import config

# Loading settings
DB_NAME = config('DB_NAME')
DB_USER = config('DB_USER')
CONTAINER_NAME = "taxi_db_container"

def restore_backup(backup_path):
    # Checking for file existence
    if not os.path.exists(backup_path):
        print(f"Error: File {backup_path} not found!")
        return

    # Warning (destructive action)
    confirm = input(f"WARNING: This will completely delete the current data in {DB_NAME}. Continue? (y/n): ")
    if confirm.lower() != 'y':
        print("Recovery canceled.")
        return

    # Command to restore
    # 'docker exec -i' allows you to transfer the contents of a file inside the container
    cmd = f"docker exec -i {CONTAINER_NAME} psql -U {DB_USER} -d {DB_NAME} < {backup_path}"

    try:
        print(f"Starting recovery from {backup_path}...")
        subprocess.run(cmd, shell=True, check=True)
        print("The database has been successfully restored!")
    except subprocess.CalledProcessError as e:
        print(f"Error during recovery: {e}")

if __name__ == "__main__":
    # Expecting a file name as an argument
    if len(sys.argv) < 2:
        print("Usage: python scripts/restore_docker.py backups/filename.sql")
    else:
        restore_backup(sys.argv[1])