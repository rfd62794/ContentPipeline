import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from produce_short import generate_voice_clip

# Test voice generation
test_text = "Penny 1%."
test_voice = "David"
output_path = Path("temp/shorts/voice_test.mp3")

print(f"Testing voice generation...")
print(f"Text: '{test_text}'")
print(f"Voice: '{test_voice}'")
print(f"Output: {output_path}")

try:
    generate_voice_clip(test_text, test_voice, output_path)
    print(f"Success! File exists: {output_path.exists()}")
    if output_path.exists():
        print(f"File size: {output_path.stat().st_size} bytes")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
