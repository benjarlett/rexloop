import subprocess
from pathlib import Path
import sys

async def run_deploy_script(websocket):
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
    try:
        process = await asyncio.create_subprocess_exec(
            "/bin/bash",
            str(deploy_script_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if stdout:
            await websocket.send(f"DEPLOY_OUTPUT: {stdout.decode().strip()}")
        if stderr:
            await websocket.send(f"DEPLOY_ERROR: {stderr.decode().strip()}")

        if process.returncode == 0:
            await websocket.send("DEPLOY_SUCCESS: Deployment script finished successfully.")
        else:
            await websocket.send(f"DEPLOY_FAILED: Deployment script exited with code {process.returncode}.")

    except Exception as e:
        await websocket.send(f"DEPLOY_ERROR: Failed to run deployment script: {e}")

    print("[Deploy] Deployment script execution finished.")
    # Do NOT exit here. Let the engine continue running to report the output.
    # The systemd service will handle restarting the engine after a successful deploy.
