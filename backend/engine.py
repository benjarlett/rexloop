

import asyncio
import websockets
import mido
import simpleaudio as sa
import threading
import argparse
import subprocess
from pathlib import Path

# --- Configuration ---
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8765
DEFAULT_TRIGGER_NOTE = 60
DEFAULT_LOOP_FILENAME = 'loop.wav'

# --- Globals ---
LOOPS_DIR = Path(__file__).parent / 'loops'
wave_obj = None
midi_message_queue = asyncio.Queue()
connected_clients = set()

def format_midi_message(msg: mido.Message) -> str:
    """Formats a mido message into a human-readable string."""
    if msg.type in ['note_on', 'note_off']:
        return f"MIDI: {msg.channel} {msg.note} {msg.velocity}"
    elif msg.type == 'control_change':
        return f"MIDI: {msg.channel} {msg.control} {msg.value}"
    return f"MIDI: {msg.type}"

def find_midi_port(name: str) -> str | None:
    """Finds the first MIDI input port containing the given name."""
    print("Searching for MIDI port...")
    available_ports = mido.get_input_names()
    print(f"Available MIDI ports: {available_ports}")
    for port in available_ports:
        if name.lower() in port.lower():
            print(f"Found MIDI port: {port}")
            return port
    return None

def midi_listener(port_name: str, trigger_note: int, loop: asyncio.AbstractEventLoop):
    """Listens for MIDI messages and puts them into a queue."""
    global wave_obj
    if not port_name:
        print("\n-- No MIDI port specified. MIDI listener will not start. --")
        return

    target_port = find_midi_port(port_name)
    if not target_port:
        print(f"ERROR: MIDI port containing '{port_name}' not found.")
        return

    try:
        with mido.open_input(target_port) as inport:
            print(f"Listening for MIDI on {inport.name}")
            for msg in inport:
                formatted_msg = format_midi_message(msg)
                loop.call_soon_threadsafe(midi_message_queue.put_nowait, formatted_msg)
                print(f"MIDI Listener: Put '{formatted_msg}' into queue.")

                if msg.type == 'note_on' and msg.note == trigger_note:
                    print(f"Trigger note {trigger_note} received! Playing loop.")
                    if wave_obj:
                        wave_obj.play()
    except (IOError, OSError) as e:
        print(f"Error opening MIDI port: {e}")

async def run_deploy_script(websocket):
    """Runs the deploy.sh script and streams its output to the client."""
    deploy_script_path = Path(__file__).parent / "deploy.sh"
    if not deploy_script_path.exists():
        await websocket.send("DEPLOY_ERROR: deploy.sh script not found!")
        return

    await websocket.send("DEPLOY_START: Starting deployment...")
    process = await asyncio.create_subprocess_shell(
        f'bash "{str(deploy_script_path)}"' ,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    # Stream stdout
    while not process.stdout.at_eof():
        line = await process.stdout.readline()
        if line:
            await websocket.send(f"DEPLOY_LOG: {line.decode().strip()}")

    # Stream stderr
    while not process.stderr.at_eof():
        line = await process.stderr.readline()
        if line:
            await websocket.send(f"DEPLOY_ERROR: {line.decode().strip()}")

    await process.wait()
    await websocket.send("DEPLOY_END: Deployment finished.")

async def midi_broadcaster():
    """Takes messages from the queue and sends them to all clients."""
    while True:
        message = await midi_message_queue.get()
        print(f"MIDI Broadcaster: Sending '{message}' to {len(connected_clients)} clients.")
        if connected_clients:
            websockets.broadcast(connected_clients, message)

async def websocket_handler(websocket):
    """Handles a single WebSocket connection."""
    connected_clients.add(websocket)
    print(f"UI Client connected: {websocket.remote_address} ({len(connected_clients)} total)")
    try:
        async for message in websocket:
            print(f"Received message from UI: {message}")
            if message == "deploy":
                await run_deploy_script(websocket)
            else:
                await websocket.send("Unknown command")
    finally:
        connected_clients.remove(websocket)
        print(f"UI Client disconnected: {websocket.remote_address} ({len(connected_clients)} total)")

async def main(args):
    """Main function to set up and run the engine."""
    global wave_obj

    wav_file_path = LOOPS_DIR / args.loop_file
    if wav_file_path.exists():
        print(f"Loading audio file: {wav_file_path}")
        wave_obj = sa.WaveObject.from_wave_file(str(wav_file_path))
    else:
        print(f"Warning: Audio file not found at {wav_file_path}")

    loop = asyncio.get_running_loop()
    midi_thread = threading.Thread(
        target=midi_listener, args=(args.midi_port, args.trigger_note, loop), daemon=True
    )
    midi_thread.start()

    asyncio.create_task(midi_broadcaster())

    async with websockets.serve(websocket_handler, args.host, args.port):
        print("\nBackend engine started!")
        await asyncio.Future()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Real-time MIDI Loop Player Engine")
    parser.add_argument("--host", type=str, default=DEFAULT_HOST, help="Host for the WebSocket server")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port for the WebSocket server")
    parser.add_argument("--midi-port", type=str, default=None, help="Name of the MIDI port to listen to")
    parser.add_argument("--trigger-note", type=int, default=DEFAULT_TRIGGER_NOTE, help="MIDI note to trigger the loop")
    parser.add_argument("--loop-file", type=str, default=DEFAULT_LOOP_FILENAME, help="Name of the audio file")
    args = parser.parse_args()

    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        print("\nShutting down.")
