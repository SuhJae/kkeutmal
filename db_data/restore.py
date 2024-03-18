import os
import subprocess


def list_docker_containers():
    """ List all running Docker containers. """
    result = subprocess.run(['docker', 'ps', '--format', '{{.Names}}'], capture_output=True, text=True)
    return result.stdout.splitlines()


def list_backup_files(backup_dir):
    """ List all files in the backup directory. """
    return [f for f in os.listdir(backup_dir) if os.path.isfile(os.path.join(backup_dir, f))]


def select_container(containers):
    """ Let the user choose a container. """
    print("Available Docker containers:")
    for i, container in enumerate(containers):
        print(f"{i + 1}. {container}")
    choice = input("Select the container number: ").strip()
    return containers[int(choice) - 1]


def select_backup_file(backup_files):
    """ Let the user choose a backup file. """
    print("Available backup files:")
    for i, file in enumerate(backup_files):
        print(f"{i + 1}. {file}")
    choice = input("Select the backup file number: ").strip()
    return backup_files[int(choice) - 1]


def main():
    backup_dir = "backup"

    # Check if backup directory exists
    if not os.path.exists(backup_dir) or not os.listdir(backup_dir):
        print("No backups found.")
        return

    # List backup files
    backup_files = list_backup_files(backup_dir)
    backup_file = select_backup_file(backup_files)

    # List Docker containers
    containers = list_docker_containers()
    if not containers:
        print("No running Docker containers found.")
        return

    mongo_container = select_container(containers)

    # MongoDB restore command
    mongodb_restore_cmd = (f"docker cp {backup_dir}/{backup_file} {mongo_container}:/data/db/backup.archive && "
                           f"docker exec {mongo_container} mongorestore --archive=/data/db/backup.archive")

    # Execute the MongoDB restore command
    print("Starting MongoDB restore...")
    subprocess.run(mongodb_restore_cmd, shell=True, check=True)

    print("Restore completed successfully.")


if __name__ == "__main__":
    main()