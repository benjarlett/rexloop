import socket

# --- Configuration ---
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8765
DEFAULT_TRIGGER_NOTE = 60  # MIDI note for C3 (for WAV playback)

def get_midi_port_names(hostname: str):
    if "Kermit" in hostname:
        # Mac settings
        return "US-800", "US-800"
    else:
        # Raspberry Pi settings
        return "pisound", "pisound"