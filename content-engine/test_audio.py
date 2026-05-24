#!/usr/bin/env python3
import sounddevice as sd
import numpy as np
import time

print('Recording 2 seconds...')
frames = []

def callback(indata, frames_count, timestamp, status):
    if status:
        print(f"Status: {status}")
    frames.append(indata.copy())

with sd.InputStream(samplerate=16000, channels=1, dtype=np.float32, callback=callback):
    time.sleep(2)

print(f'Recorded {len(frames)} frames')
