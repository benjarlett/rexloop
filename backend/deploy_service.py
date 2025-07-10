

import asyncio
import websockets
import subprocess
from pathlib import Path
import json

# --- Configuration ---
LOCAL_HOST = "0.0.0.0" # Listen on all network interfaces
LOCAL_PORT = 8766        # A new port for the deploy service

# --- Globals ---
PROJECT_ROOT = Path(__file__).parent.parent # Assumes deploy_service.py is in backend/
REFRESH_SCRIPT_PATH = PROJECT_ROOT / "refresh.sh"

async def deploy_handler(websocket):
    print(f"[DeployService] Client connected: {websocket.remote_address}")
    try:
        async for message in websocket:
            print(f"[DeployService] Received command: {message}")
            try:
                msg_data = json.loads(message)
                if msg_data.get('command') == 'deploy':
                    await run_refresh_script(websocket)
                else:
                    await websocket.send(json.dumps({'type': 'deploy_status', 'status': 'error', 'message': 'Unknown command'}))
            except json.JSONDecodeError:
                await websocket.send(json.dumps({'type': 'deploy_status', 'status': 'error', 'message': 'Invalid JSON command'}))
    except websockets.ConnectionClosed:
        print(f"[DeployService] Client disconnected: {websocket.remote_address}")
    except Exception as e:
        print(f"[DeployService] Error in handler: {e}")

async def run_refresh_script(websocket):
    print(f"[DeployService] Attempting to run refresh script: {REFRESH_SCRIPT_PATH}")
    if not REFRESH_SCRIPT_PATH.exists():
        print(f"[DeployService] ERROR: refresh.sh script not found at {REFRESH_SCRIPT_PATH}!")
        await websocket.send(json.dumps({'type': 'deploy_status', 'status': 'error', 'message': 'refresh.sh not found!'}))
        return

    await websocket.send(json.dumps({'type': 'deploy_status', 'status': 'started', 'message': 'Starting full refresh...'}))
    try:
        process = await asyncio.create_subprocess_shell(
            f'bash "{str(REFRESH_SCRIPT_PATH)}'
            ,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(PROJECT_ROOT) # Ensure script runs from project root
        )
        print(f"[DeployService] Subprocess started with PID: {process.pid}")

        # Stream stdout
        async for line in process.stdout:
            decoded_line = line.decode().strip()
            print(f"[DeployService] STDOUT: {decoded_line}")
            await websocket.send(json.dumps({'type': 'deploy_status', 'status': 'log', 'message': decoded_line}))

        # Stream stderr
        async for line in process.stderr:
            decoded_line = line.decode().strip()
            print(f"[DeployService] STDERR: {decoded_line}")
            await websocket.send(json.dumps({'type': 'deploy_status', 'status': 'error', 'message': decoded_line}))

        returncode = await process.wait()
        print(f"[DeployService] Subprocess finished with return code: {returncode}")
        if returncode == 0:
            await websocket.send(json.dumps({'type': 'deploy_status', 'status': 'completed', 'message': 'Deployment finished successfully.'}))
        else:
            await websocket.send(json.dumps({'type': 'deploy_status', 'status': 'failed', 'message': f'Deployment failed with code {returncode}.'}))

    except Exception as e:
        print(f"[DeployService] EXCEPTION: {e}")
        await websocket.send(json.dumps({'type': 'deploy_status', 'status': 'error', 'message': f'An error occurred: {e}'}))

async def main():
    async with websockets.serve(deploy_handler, LOCAL_HOST, LOCAL_PORT):
        print(f"[DeployService] Deployment service started at ws://{LOCAL_HOST}:{LOCAL_PORT}")
        await asyncio.Future() # Run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[DeployService] Shutting down.")

