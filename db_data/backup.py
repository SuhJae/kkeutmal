import os
import subprocess
from datetime import datetime


def list_docker_containers():
    """ List all running Docker containers. """
    result = subprocess.run(['docker', 'ps', '--format', '{{.Names}}'], capture_output=True, text=True)
    return result.stdout.splitlines()


def select_container(containers):
    """ Let the user choose a container. """
    print("Available Docker containers:")
    for i, container in enumerate(containers):
        print(f"{i + 1}. {container}")
    choice = input("Select the container number: ").strip()
    return containers[int(choice) - 1]


def main():
    # Get the current date and time in the specified format
    date_format = "%Y%m%d-%H%M%S"
    current_date = datetime.now().strftime(date_format)

    # Create backup directory if it doesn't exist
    backup_dir = "backup"
    os.makedirs(backup_dir, exist_ok=True)

    # List Docker containers
    containers = list_docker_containers()
    if not containers:
        print("No running Docker containers found.")
        return

    mongo_container = select_container(containers)

    # MongoDB backup command
    mongodb_backup_dir = f"mongodb_backup_{current_date}"
    mongodb_backup_cmd = (f"docker exec {mongo_container} mongodump --archive=/data/db/{mongodb_backup_dir}.archive")

    # Execute the MongoDB backup command
    print("Starting MongoDB backup...")
    subprocess.run(mongodb_backup_cmd, shell=True, check=True)

    # Copy backup from container to host
    copy_cmd = (f"docker cp {mongo_container}:/data/db/{mongodb_backup_dir}.archive {backup_dir}/")
    subprocess.run(copy_cmd, shell=True, check=True)

    print("Backup completed successfully.")

    # Remove backup from container
    remove_cmd = (f"docker exec {mongo_container} rm -rf /data/db/{mongodb_backup_dir}.archive")

    print("Removing backup from container...")
    subprocess.run(remove_cmd, shell=True, check=True)

    print("Backup removed from container successfully.")


if __name__ == "__main__":
    main()