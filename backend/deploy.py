import subprocess
from pathlib import Path
import sys

async def run_deploy_script(websocket):
    print("[Deploy] run_deploy_script called.")
    """Launches the refresh.sh script as a detached process and exits the current process."""
    deploy_script_path = Path(__file__).parent / "deploy.sh"
    print(f"[Deploy] Launching deploy script: {deploy_script_path}")
    if not deploy_script_path.exists():
        print(f"[Deploy] ERROR: deploy.sh script not found at {deploy_script_path}!")
        await websocket.send("DEPLOY_ERROR: deploy.sh script not found!")
        return

    # Launch the deploy.sh script as a detached process
    # This allows the current Python process to exit immediately,
    # letting systemd restart it with the new code after refresh.sh completes.
    log_file_path = "/tmp/deploy_log.txt"
    print(f"[Deploy] Attempting to run deploy script: {deploy_script_path}")
    try:
        with open(log_file_path, "w") as log_file:
            process = subprocess.run(
                [str(deploy_script_path)],
                executable="/bin/bash", # Explicitly use bash
                stdout=log_file,
                stderr=log_file,
                text=True  # Capture output as text
            )
        print(f"[Deploy] Subprocess finished with return code: {process.returncode}")

        # Read the log file and send its content to the WebSocket
        with open(log_file_path, "r") as log_file:
            output = log_file.read()
            await websocket.send(f"DEPLOY_LOG_START\n{output}\nDEPLOY_LOG_END")

        if process.returncode == 0:
            await websocket.send("DEPLOY_SUCCESS: Deployment script finished successfully.")
        else:
            await websocket.send(f"DEPLOY_FAILED: Deployment script exited with code {process.returncode}.")

    except FileNotFoundError:
        await websocket.send(f"DEPLOY_ERROR: Bash executable not found at /bin/bash. Check system path.")
        print(f"[Deploy] Error: Bash executable not found at /bin/bash.")
    except Exception as e:
        await websocket.send(f"DEPLOY_ERROR: Failed to run deployment script: {e}")
        print(f"[Deploy] Error running deployment script: {e}")

    print(f"[Deploy] Deployment script execution finished. Log at {log_file_path}")
