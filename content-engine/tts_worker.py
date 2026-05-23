import sys
import pyttsx3

def main():
    text = sys.argv[1]
    output_path = sys.argv[2]
    voice_name = sys.argv[3] if len(sys.argv) > 3 else "David"
    
    engine = pyttsx3.init()
    
    # Set voice
    voices = engine.getProperty('voices')
    for v in voices:
        if voice_name.lower() in v.name.lower():
            engine.setProperty('voice', v.id)
            break
    
    engine.save_to_file(text, output_path)
    engine.runAndWait()

if __name__ == "__main__":
    main()
