import asyncio
import websockets
import json
import mido
from pathlib import Path

from deploy import run_deploy_script
from midi import list_midi_files_in_loops_dir, play_midi_file
import midi
import audio

connected_clients = set()
LOOPS_DIR = Path(__file__).parent / 'loops'

async def midi_broadcaster(queue: asyncio.Queue):
    """Takes messages from the queue and sends them to all clients."""
    while True:
        message = await queue.get()
        if connected_clients:
            websockets.broadcast(connected_clients, message)

async def websocket_handler(websocket, queue: asyncio.Queue):
    """Handles a single WebSocket connection."""
    connected_clients.add(websocket)
    print(f"UI Client connected: {websocket.remote_address} ({len(connected_clients)} total)")
    try:
        async for message in websocket:
            print(f"[Server] Raw message received from UI: {message}") # Added for debugging
            try:
                msg_data = json.loads(message)
                if msg_data.get('command') == 'deploy':
                    print("[Server] Received deploy command. Calling run_deploy_script...")
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
                                midi.loaded_midi_file = mido.MidiFile(str(midi_file_path))
                                midi.current_midi_trigger_note = trigger_note
                                
                                # Load the corresponding WAV file
                                wav_filename = midi_file_path.with_suffix('.wav').name
                                audio.load_audio_file(wav_filename)

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
