import simpleaudio as sa
from pathlib import Path

LOOPS_DIR = Path(__file__).parent / 'loops'
wave_obj = None

def load_audio_file(filename):
    """Loads an audio file."""
    global wave_obj
    wav_file_path = LOOPS_DIR / filename
    if wav_file_path.exists():
        print(f"Loading audio file: {wav_file_path}")
        wave_obj = sa.WaveObject.from_wave_file(str(wav_file_path))
    else:
        print(f"Warning: Audio file not found at {wav_file_path}")

def play_audio():
    """Plays the loaded audio file."""
    if wave_obj:
        wave_obj.play()
