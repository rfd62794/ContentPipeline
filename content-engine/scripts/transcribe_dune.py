import sys
import subprocess

sys.path.insert(0, '.')
from review_session import transcribe

wav_path = 'C:/Users/cheat/Videos/Dune Awakening/temp.wav'

subprocess.run([
    'ffmpeg', '-i', 'C:/Users/cheat/Videos/2026-05-24 14-50-43.mp4',
    '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', wav_path
])

segments = transcribe(wav_path, 'base', device='cuda')

for seg in segments:
    print(f"[{seg['start']:.2f}] {seg['text']}")
