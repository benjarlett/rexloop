import mido
import asyncio
from pathlib import Path

LOOPS_DIR = Path(__file__).parent / 'loops'
midi_out_port = None
loaded_midi_file = None
current_midi_trigger_note = None

def format_midi_message(msg: mido.Message) -> str:
    """Formats a mido message into a human-readable string."""
    if msg.type in ['note_on', 'note_off']:
        return f"MIDI: {msg.channel} {msg.note} {msg.velocity}"
    elif msg.type == 'control_change':
        return f"MIDI: {msg.channel} {msg.control} {msg.value}"
    return f"MIDI: {msg.type}"

def find_midi_port(name: str, is_output: bool = False):
    """Finds the first MIDI input or output port containing the given name."""
    print(f"Searching for MIDI {'output' if is_output else 'input'} port...")
    available_ports = mido.get_output_names() if is_output else mido.get_input_names()
    print(f"Available MIDI {'output' if is_output else 'input'} ports: {available_ports}")
    for port in available_ports:
        if name.lower() in port.lower():
            print(f"Found MIDI {'output' if is_output else 'input'} port: {port}")
            return port
    return None

async def play_midi_file(queue: asyncio.Queue):
    """Plays a loaded MIDI file through the MIDI output port."""
    global midi_out_port
    if not midi_out_port:
        print("Error: MIDI output port not open.")
        return

    print(f"Playing MIDI file: {loaded_midi_file.filename}")
    for msg in loaded_midi_file.play():
        midi_out_port.send(msg)
        # Send MIDI OUT activity to the frontend
        midi_activity_message = {
            'type': 'midi_activity',
            'direction': 'out',
            'message': format_midi_message(msg)
        }
        asyncio.get_running_loop().call_soon_threadsafe(queue.put_nowait, midi_activity_message)
        await asyncio.sleep(msg.time)
    print("Finished playing MIDI file.")

def list_midi_files_in_loops_dir() -> list[str]:
    """Lists all .mid files in the loops directory."""
    midi_files = []
    if LOOPS_DIR.exists() and LOOPS_DIR.is_dir():
        for f in LOOPS_DIR.iterdir():
            if f.is_file() and f.suffix.lower() == '.mid':
                midi_files.append(f.name)
    return sorted(midi_files)

def midi_listener(port_name: str, trigger_note: int, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue):
    """Listens for MIDI messages and puts them into a queue."""
    from audio import play_audio
    global loaded_midi_file, current_midi_trigger_note
    if not port_name:
        print("\n-- No MIDI input port specified. MIDI listener will not start. --")
        return

    target_port = find_midi_port(port_name, is_output=False)
    if not target_port:
        print(f"ERROR: MIDI input port containing '{port_name}' not found.")
        return

    try:
        with mido.open_input(target_port) as inport:
            print(f"Successfully opened MIDI input port: {inport.name}")
            print(f"Listening for MIDI on {inport.name}")
            for msg in inport:
                midi_activity_message = {
                    'type': 'midi_activity',
                    'direction': 'in',
                    'message': format_midi_message(msg)
                }
                loop.call_soon_threadsafe(queue.put_nowait, midi_activity_message)

                if msg.type == 'note_on' and msg.note == trigger_note:
                    print(f"Trigger note {trigger_note} received! Playing WAV loop.")
                    play_audio()
                elif msg.type == 'note_on' and current_midi_trigger_note is not None and msg.note == current_midi_trigger_note:
                    print(f"MIDI Play Trigger note {current_midi_trigger_note} received! Playing MIDI file.")
                    if loaded_midi_file:
                        asyncio.run_coroutine_threadsafe(play_midi_file(queue), loop)
                    else:
                        print("Warning: No MIDI file loaded to play.")
    except (IOError, OSError) as e:
        print(f"Error opening MIDI input port: {e}")
