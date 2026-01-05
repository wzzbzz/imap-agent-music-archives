import os
import json
import time
import google.generativeai as genai
import google.api_core.exceptions


# --- CONFIGURATION ---
GEMINI_KEY = 'AIzaSyCozHcgPg-9vOw1EMMtlCauC0RMYb0q9Og'

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('models/gemini-3-flash-preview')


def ask_gemini_with_retry(prompt, max_retries=5):
    """Handles 429 errors with exponential backoff."""
    for attempt in range(max_retries):
        try:
            response = model.generate_content(
                prompt, 
                generation_config={"response_mime_type": "application/json"}
            )
            return json.loads(response.text)
        except google.api_core.exceptions.ResourceExhausted:
            wait_time = (attempt + 1) * 12  # 12s, 24s, 36s...
            print(f"⏳ Rate limit (429) hit. Sleeping {wait_time}s before retry...")
            time.sleep(wait_time)
        except Exception as e:
            if "429" in str(e): # Backup check for 429 string
                time.sleep(15)
                continue
            raise e
    raise Exception("Max retries exceeded for Gemini API")

def prompt_from_data(data):
    try:
        # Sanitize the body to prevent JSON escape errors
        print("🧠 Gemini is analyzing...")
        prompt = f"""
        Respond with valid JSON only. Escape all backslashes properly (e.g., use \\\\ for literal \ $$.

        Extract this music release newsletter into a JSON object.  Use the slugified file path. 

        Note:  Numbers on files do not necessarily correlate to the track order of the release;  use the track order as found in the message body


        SUBJECT: {data['subject']}
        ATTACHMENTS AVAILABLE: {data['attachments']}
        BODY: {data['body']}

        SCHEMA: 
        {{ 
        "release_number": int, 
        "release_image": "string",
        "tracks": [ 
            {{ 
            "track_num": int, 
            "title": "string", 
            "credits": "string", 
            "date_written": "string",
            "lyrics": "string", 
            "audio_file": "slugified_filename_here",
            "track_image": "image_file"

            }}
        ] 
        }}
        """
        return prompt
        

    except Exception as e:
        print(f"❌ Error on {data['subject']}: {e}")
   

def reprocess_episode(arguments):
    episode = arguments.get('release_number')
    base_dir = arguments.get('base_dir')
    ri = arguments.get('release_indicator')
    
    folder_name = f"{ri}_{episode}"
    raw_json_path = os.path.join(base_dir,folder_name,'raw.json')
    
    with open(raw_json_path,'r') as f:
        raw_data = json.load(f)
        prompt = prompt_from_data(raw_data)
        structured_data = ask_gemini_with_retry(prompt)
        print("about to write the file...")
        with open(os.path.join(base_dir,folder_name, "metadata.json"), "w") as f:
            print("writing the file")
            json.dump(structured_data, f, indent=4)
    print("done!")
    return

def run_archive_pipeline(arguments):

    print("🚀 deciphering raw emails...")
    BASE_DIR = arguments.get('base_dir')
    ri = arguments.get('release_indicator')

    print("-" * 50)
    count=0
    limit=100

    PROCESSED_FILE = os.path.join(BASE_DIR,"processed.json")

    # Check if the file exists; if not, start with an empty list
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, 'r') as f:
            processed_ids = json.load(f)
    else:
        processed_ids = []

    for folder in os.listdir(BASE_DIR):
        if count>limit:
            break

        if folder.startswith(f"{ri}_"):
            print(f"processing {folder}")
            raw_json_path = os.path.join(BASE_DIR, folder, "raw.json")
            
            with open(raw_json_path, 'r') as raw_json:
                raw_data = json.load(raw_json)
                if(processed_ids.__contains__(raw_data['uid'])):
                    print(f"{raw_data['subject']} already processed, skipping...")
                    continue


                prompt = prompt_from_data(raw_data)
          
                # Call Gemini with the new retry logic
                structured_data = ask_gemini_with_retry(prompt)
        
                release_num = structured_data.get("release_number")
                final_issue_dir = os.path.join(BASE_DIR, f"{ri}_{release_num}")

                print(f"📥 Archiving {ri} {release_num}...")
 
                with open(os.path.join(final_issue_dir, "metadata.json"), "w") as f:
                    json.dump(structured_data, f, indent=4)
                
                processed_ids.append(raw_data['uid'])
                # Save back to file
                with open(PROCESSED_FILE, 'w') as f:
                    json.dump(processed_ids, f)
                print(f"✅ Success: {ri} {release_num} archived.")


                count=count+1
                
                # Mandatory pause to prevent hitting the 20-request limit again
                print("⏳ Throttling: Waiting 5 seconds...")
                time.sleep(5)


                
            
    print("-" * 50)
if __name__ == "__main__":
    arguments = {
        "base_dir":"sonic_twist_archives",
        "release_indicator":"Issue",
        "release_number":36
    }
    reprocess_episode(arguments)