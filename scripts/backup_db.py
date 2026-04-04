import subprocess
from datetime import datetime
from decouple import config

# Loading settings from .env
DB_NAME = config('DB_NAME')
DB_USER = config('DB_USER')
CONTAINER_NAME = "taxi_db_container"

# Creating a file name
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_file = f"backups/taxi_db_{timestamp}.sql"

# Docker command
# We use 'docker exec' to call pg_dump inside the container
cmd = f"docker exec {CONTAINER_NAME} pg_dump -U {DB_USER} {DB_NAME} > {backup_file}"

try:
    print(f"Starting backup of {DB_NAME}...")
    subprocess.run(cmd, shell=True, check=True)
    print(f"Successfully created: {backup_file}")
except subprocess.CalledProcessError as e:
    print(f"Error during backup: {e}")