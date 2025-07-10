import asyncio
import websockets
import mido
import simpleaudio as sa
import threading
import argparse
import subprocess
from pathlib import Path
import json

from typing import Optional

# --- Configuration ---
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8765
DEFAULT_TRIGGER_NOTE = 60  # MIDI note for C3 (for WAV playback)
DEFAULT_LOOP_FILENAME = 'loop.wav'
MIDI_IN_PORT_NAME = 'pisound' # Name of the MIDI input port to listen to
MIDI_OUT_PORT_NAME = 'pisound' # Name of the MIDI output port to send to

# --- Globals ---
LOOPS_DIR = Path(__file__).parent / 'loops'
wave_obj = None
midi_message_queue = asyncio.Queue()
connected_clients = set()
midi_out_port = None
loaded_midi_file = None
current_midi_trigger_note = None # New global for dynamic MIDI trigger note

def format_midi_message(msg: mido.Message) -> str:
    """Formats a mido message into a human-readable string."""
    if msg.type in ['note_on', 'note_off']:
        return f"MIDI: {msg.channel} {msg.note} {msg.velocity}"
    elif msg.type == 'control_change':
        return f"MIDI: {msg.channel} {msg.control} {msg.value}"
    return f"MIDI: {msg.type}"

def find_midi_port(name: str, is_output: bool = False) -> Optional[str]:
    """Finds the first MIDI input or output port containing the given name."""
    print(f"Searching for MIDI {'output' if is_output else 'input'} port...")
    available_ports = mido.get_output_names() if is_output else mido.get_input_names()
    print(f"Available MIDI {'output' if is_output else 'input'} ports: {available_ports}")
    for port in available_ports:
        if name.lower() in port.lower():
            print(f"Found MIDI {'output' if is_output else 'input'} port: {port}")
            return port
    return None

async def play_midi_file(midi_file: mido.MidiFile):
    """Plays a loaded MIDI file through the MIDI output port."""
    global midi_out_port
    if not midi_out_port:
        print("Error: MIDI output port not open.")
        return

    print(f"Playing MIDI file: {midi_file.filename}")
    for msg in midi_file.play():
        midi_out_port.send(msg)
        formatted_msg = format_midi_message(msg) # Format the outgoing message
        asyncio.get_running_loop().call_soon_threadsafe(midi_message_queue.put_nowait, formatted_msg) # Put into queue
        await asyncio.sleep(msg.time) # Wait for the message's delta time
    print("Finished playing MIDI file.")

def list_midi_files_in_loops_dir() -> list[str]:
    """Lists all .mid files in the loops directory."""
    midi_files = []
    if LOOPS_DIR.exists() and LOOPS_DIR.is_dir():
        for f in LOOPS_DIR.iterdir():
            if f.is_file() and f.suffix.lower() == '.mid':
                midi_files.append(f.name)
    return sorted(midi_files)

def midi_listener(port_name: str, trigger_note: int, loop: asyncio.AbstractEventLoop):
    """Listens for MIDI messages and puts them into a queue."""
    global wave_obj, loaded_midi_file, current_midi_trigger_note
    if not port_name:
        print("\n-- No MIDI input port specified. MIDI listener will not start. --")
        return

    target_port = find_midi_port(port_name, is_output=False)
    if not target_port:
        print(f"ERROR: MIDI input port containing '{port_name}' not found.")
        return

    try:
        with mido.open_input(target_port) as inport:
            print(f"Listening for MIDI on {inport.name}")
            for msg in inport:
                formatted_msg = format_midi_message(msg)
                loop.call_soon_threadsafe(midi_message_queue.put_nowait, formatted_msg)

                if msg.type == 'note_on' and msg.note == trigger_note:
                    print(f"Trigger note {trigger_note} received! Playing WAV loop.")
                    if wave_obj:
                        wave_obj.play()
                elif msg.type == 'note_on' and current_midi_trigger_note is not None and msg.note == current_midi_trigger_note:
                    print(f"MIDI Play Trigger note {current_midi_trigger_note} received! Playing MIDI file.")
                    if loaded_midi_file:
                        asyncio.run_coroutine_threadsafe(play_midi_file(loaded_midi_file), loop)
                    else:
                        print("Warning: No MIDI file loaded to play.")
    except (IOError, OSError) as e:
        print(f"Error opening MIDI input port: {e}")

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
        ['bash', str(deploy_script_path)],
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

async def midi_broadcaster():
    """Takes messages from the queue and sends them to all clients."""
    while True:
        message = await midi_message_queue.get()
        if connected_clients:
            websockets.broadcast(connected_clients, message)

async def websocket_handler(websocket):
    """Handles a single WebSocket connection."""
    global loaded_midi_file, current_midi_trigger_note
    connected_clients.add(websocket)
    print(f"UI Client connected: {websocket.remote_address} ({len(connected_clients)} total)")
    try:
        async for message in websocket:
            print(f"Received message from UI: {message}")
            try:
                msg_data = json.loads(message)
                if msg_data.get('command') == 'deploy':
                    await run_deploy_script(websocket)
                elif msg_data.get('command') == 'list_midi_files':
                    midi_files = list_midi_files_in_loops_dir()
                    await websocket.send(json.dumps({'type': 'midi_file_list', 'files': midi_files}))
                    print(f"Sent MIDI file list: {midi_files}")
                elif msg_data.get('command') == 'load_midi':
                    midi_filename = msg_data.get('filename')
                    trigger_note = msg_data.get('trigger_note')
                    if midi_filename and trigger_note is not None:
                        midi_file_path = LOOPS_DIR / midi_filename
                        if midi_file_path.exists():
                            try:
                                loaded_midi_file = mido.MidiFile(str(midi_file_path))
                                current_midi_trigger_note = trigger_note
                                await websocket.send(f"MIDI_LOADED: {midi_filename} (Trigger: {trigger_note})")
                                print(f"Loaded MIDI file: {midi_filename} (Trigger: {trigger_note})")
                            except Exception as e:
                                await websocket.send(f"MIDI_ERROR: Could not load MIDI file {midi_filename}: {e}")
                                print(f"Error loading MIDI file {midi_filename}: {e}")
                        else:
                            await websocket.send(f"MIDI_ERROR: MIDI file not found: {midi_filename}")
                            print(f"MIDI file not found: {midi_filename}")
                    else:
                        await websocket.send("MIDI_ERROR: Missing filename or trigger_note for load_midi command.")
                        print("Missing filename or trigger_note for load_midi command.")
                else:
                    await websocket.send("Unknown command")
            except json.JSONDecodeError:
                # Handle non-JSON messages (like simple MIDI messages)
                print(f"Received non-JSON message: {message}")
                await websocket.send(f"Echo from engine: {message}")
    finally:
        connected_clients.remove(websocket)
        print(f"UI Client disconnected: {websocket.remote_address} ({len(connected_clients)} total)")

async def main(args):
    """Main function to set up and run the engine."""
    global wave_obj, midi_out_port

    # Load the audio file
    wav_file_path = LOOPS_DIR / args.loop_file
    if wav_file_path.exists():
        print(f"Loading audio file: {wav_file_path}")
        wave_obj = sa.WaveObject.from_wave_file(str(wav_file_path))
    else:
        print(f"Warning: Audio file not found at {wav_file_path}")

    # Open MIDI output port
    if args.midi_out_port:
        output_port_name = find_midi_port(args.midi_out_port, is_output=True)
        if output_port_name:
            try:
                midi_out_port = mido.open_output(output_port_name)
                print(f"Opened MIDI output port: {midi_out_port.name}")
            except (IOError, OSError) as e:
                print(f"Error opening MIDI output port: {e}")
        else:
            print(f"Warning: MIDI output port containing '{args.midi_out_port}' not found.")

    loop = asyncio.get_running_loop()
    midi_thread = threading.Thread(
        target=midi_listener, args=(args.midi_in_port, args.trigger_note, loop), daemon=True
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
    parser.add_argument("--midi-in-port", type=str, default=MIDI_IN_PORT_NAME, help="Name of the MIDI input port to listen to (e.g., 'pisound')")
    parser.add_argument("--midi-out-port", type=str, default=MIDI_OUT_PORT_NAME, help="Name of the MIDI output port to send to (e.g., 'pisound')")
    parser.add_argument("--trigger-note", type=int, default=DEFAULT_TRIGGER_NOTE, help="MIDI note number to trigger the WAV loop")
    parser.add_argument("--loop-file", type=str, default=DEFAULT_LOOP_FILENAME, help="Name of the audio file in the 'loops' directory")
    args = parser.parse_args()

    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        print("\nShutting down.")

async def midi_broadcaster():
    """Takes messages from the queue and sends them to all clients."""
    while True:
        message = await midi_message_queue.get()
        if connected_clients:
            websockets.broadcast(connected_clients, message)

async def websocket_handler(websocket):
    """Handles a single WebSocket connection."""
    global loaded_midi_file, current_midi_trigger_note
    connected_clients.add(websocket)
    print(f"UI Client connected: {websocket.remote_address} ({len(connected_clients)} total)")
    try:
        async for message in websocket:
            print(f"Received message from UI: {message}")
            try:
                msg_data = json.loads(message)
                if msg_data.get('command') == 'deploy':
                    await run_deploy_script(websocket)
                elif msg_data.get('command') == 'list_midi_files':
                    midi_files = list_midi_files_in_loops_dir()
                    await websocket.send(json.dumps({'type': 'midi_file_list', 'files': midi_files}))
                    print(f"Sent MIDI file list: {midi_files}")
                elif msg_data.get('command') == 'load_midi':
                    midi_filename = msg_data.get('filename')
                    trigger_note = msg_data.get('trigger_note')
                    if midi_filename and trigger_note is not None:
                        midi_file_path = LOOPS_DIR / midi_filename
                        if midi_file_path.exists():
                            try:
                                loaded_midi_file = mido.MidiFile(str(midi_file_path))
                                current_midi_trigger_note = trigger_note
                                await websocket.send(f"MIDI_LOADED: {midi_filename} (Trigger: {trigger_note})")
                                print(f"Loaded MIDI file: {midi_filename} (Trigger: {trigger_note})")
                            except Exception as e:
                                await websocket.send(f"MIDI_ERROR: Could not load MIDI file {midi_filename}: {e}")
                                print(f"Error loading MIDI file {midi_filename}: {e}")
                        else:
                            await websocket.send(f"MIDI_ERROR: MIDI file not found: {midi_filename}")
                            print(f"MIDI file not found: {midi_filename}")
                    else:
                        await websocket.send("MIDI_ERROR: Missing filename or trigger_note for load_midi command.")
                        print("Missing filename or trigger_note for load_midi command.")
                else:
                    await websocket.send("Unknown command")
            except json.JSONDecodeError:
                # Handle non-JSON messages (like simple MIDI messages)
                print(f"Received non-JSON message: {message}")
                await websocket.send(f"Echo from engine: {message}")
    finally:
        connected_clients.remove(websocket)
        print(f"UI Client disconnected: {websocket.remote_address} ({len(connected_clients)} total)")

async def main(args):
    """Main function to set up and run the engine."""
    global wave_obj, midi_out_port

    # Load the audio file
    wav_file_path = LOOPS_DIR / args.loop_file
    if wav_file_path.exists():
        print(f"Loading audio file: {wav_file_path}")
        wave_obj = sa.WaveObject.from_wave_file(str(wav_file_path))
    else:
        print(f"Warning: Audio file not found at {wav_file_path}")

    # Open MIDI output port
    if args.midi_out_port:
        output_port_name = find_midi_port(args.midi_out_port, is_output=True)
        if output_port_name:
            try:
                midi_out_port = mido.open_output(output_port_name)
                print(f"Opened MIDI output port: {midi_out_port.name}")
            except (IOError, OSError) as e:
                print(f"Error opening MIDI output port: {e}")
        else:
            print(f"Warning: MIDI output port containing '{args.midi_out_port}' not found.")

    loop = asyncio.get_running_loop()
    midi_thread = threading.Thread(
        target=midi_listener, args=(args.midi_in_port, args.trigger_note, loop), daemon=True
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
    parser.add_argument("--midi-in-port", type=str, default=MIDI_IN_PORT_NAME, help="Name of the MIDI input port to listen to (e.g., 'pisound')")
    parser.add_argument("--midi-out-port", type=str, default=MIDI_OUT_PORT_NAME, help="Name of the MIDI output port to send to (e.g., 'pisound')")
    parser.add_argument("--trigger-note", type=int, default=DEFAULT_TRIGGER_NOTE, help="MIDI note number to trigger the WAV loop")
    parser.add_argument("--loop-file", type=str, default=DEFAULT_LOOP_FILENAME, help="Name of the audio file in the 'loops' directory")
    args = parser.parse_args()

    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        print("\nShutting down.")