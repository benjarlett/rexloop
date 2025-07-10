import os

log_file_path = "/tmp/deploy_log.txt"

try:
    with open(log_file_path, "w") as f:
        f.write("Test log entry from test_log_write.py\n")
    print(f"Successfully wrote to {log_file_path}")
except Exception as e:
    print(f"Error writing to {log_file_path}: {e}")

