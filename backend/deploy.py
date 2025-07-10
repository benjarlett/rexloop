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
    subprocess.Popen(
        ['/bin/bash', str(deploy_script_path)],
        stdout=subprocess.DEVNULL, # Redirect stdout to /dev/null
        stderr=subprocess.DEVNULL, # Redirect stderr to /dev/null
        start_new_session=True # Detach from current session
    )
    print("[Deploy] deploy.sh launched as detached process. Exiting current engine process.")
    # Send a message to the frontend indicating deployment started, but logs won't stream.
    await websocket.send("DEPLOY_STARTED_DETACHED: Backend is updating. Check Pi's journalctl for full logs.")
    # Exit the current process so systemd can restart it with the new code
    # This will cause the frontend to lose connection temporarily.
    sys.exit(0)
