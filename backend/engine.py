import asyncio
import argparse
import threading
import functools
import socket

import websockets
import mido

from config import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_TRIGGER_NOTE,
    get_midi_port_names
)
from audio import load_audio_file
from midi import midi_listener, find_midi_port
from server import websocket_handler, midi_broadcaster
import midi

async def main(args):
    """Main function to set up and run the engine."""
    # Create the MIDI message queue inside the main async function
    # to ensure it's attached to the correct event loop.
    midi_message_queue = asyncio.Queue()

    

    midi_in_port_name, midi_out_port_name = get_midi_port_names(args.hostname)

    # Open MIDI output port
    if midi_out_port_name:
        output_port_name = find_midi_port(midi_out_port_name, is_output=True)
        if output_port_name:
            try:
                midi.midi_out_port = mido.open_output(output_port_name)
                print(f"Opened MIDI output port: {midi.midi_out_port.name}")
            except (IOError, OSError) as e:
                print(f"Error opening MIDI output port: {e}")
        else:
            print(f"Warning: MIDI output port containing '{midi_out_port_name}' not found.")

    loop = asyncio.get_running_loop()
    midi_thread = threading.Thread(
        target=midi_listener, args=(midi_in_port_name, args.trigger_note, loop, midi_message_queue), daemon=True
    )
    midi_thread.start()

    # Start the MIDI broadcaster task
    broadcaster_task = asyncio.create_task(midi_broadcaster(midi_message_queue))

    # Pass the queue to the websocket handler
    handler = functools.partial(websocket_handler, queue=midi_message_queue)

    async with websockets.serve(handler, args.host, args.port):
        print("\nBackend engine started!")
        # Keep the server running until it's cancelled
        await asyncio.Future()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Real-time MIDI Loop Player Engine")
    parser.add_argument("--host", type=str, default=DEFAULT_HOST, help="Host for the WebSocket server")
    parser.add_argument("--hostname", type=str, default=socket.gethostname(), help="Hostname of the machine, used for MIDI port detection.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port for the WebSocket server")
    
    parser.add_argument("--trigger-note", type=int, default=DEFAULT_TRIGGER_NOTE, help="MIDI note number to trigger the WAV loop")
    parser.add_argument("--loop-file", type=str, default=None, help="Name of the audio file in the 'loops' directory")
    args = parser.parse_args()

    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        print("\nShutting down.")