import os
import json
from mutagen.mp3 import MP3

def get_duration(file_path):
    """Returns duration in seconds as an integer."""
    try:
        audio = MP3(file_path)
        return int(audio.info.length)
    except Exception as e:
        print(f"Could not read {file_path}: {e}")
        return 0

def update_archives(root_dir):

    # Walk through every folder in your archives
    for root, dirs, files in os.walk(root_dir):

     
        if 'metadata.json' in files:

            json_path = os.path.join(root, 'metadata.json')
            
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            
            for track in data.get('tracks', []):
                audio_filename = track.get('audio_file')
                folder_name = os.path.basename(root)
            
                print(f"\n========================================")
                print(f"📂 CURRENT DIRECTORY: {folder_name}")
                print(f"📍 FULL PATH: {root}")
                print(f"========================================")
                if audio_filename == None:
                    exit()
                    break
                # Assumes audio files are in the same folder or an 'audio' subfolder
                audio_path = os.path.join(root, audio_filename)
                
                # Check for 'audio' subfolder if not found in root
                if not os.path.exists(audio_path):
                    audio_path = os.path.join(root, 'audio', audio_filename)

                if os.path.exists(audio_path):
                    duration = get_duration(audio_path)
                    track['duration'] = duration
                    print(f"Updated: {track['title']} -> {duration}s")
                    updated = True
                else:
                    print(f"Warning: Audio file not found: {audio_path}")

            if updated:
                with open(json_path, 'w') as f:
                    json.dump(data, f, indent=4)
                print(f"Successfully saved {json_path}")

if __name__ == "__main__":
    # Run this from the folder containing your archives
    update_archives('.')