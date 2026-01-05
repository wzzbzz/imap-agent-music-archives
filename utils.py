import re
import os
import json
import time
import tempfile

from ffmpeg_normalize import FFmpegNormalize, MediaFile

def clean_text(text):
    if not text: return ""
    return text.replace('\r', '').replace('\n', ' ').strip()


def sanitize_for_json(text):
    r"""Prevents 'Invalid \escape' errors by cleaning problematic characters."""
    if not text: return ""
    # Replace backslashes with forward slashes and convert double quotes to single
    # This prevents the AI from generating unescaped control characters in JSON strings
    return text.replace('\\', '/').replace('"', "'")

def slugify_filename(filename):
    name, ext = os.path.splitext(filename)
    name = name.lower()
    name = re.sub(r'[^a-z0-9]+', '_', name)
    name = re.sub(r'_+', '_', name).strip('_')
    return f"{name}{ext.lower()}"



def get_release_number_fallback(subject):
    match = re.search(r'(?:Issue|#|Volume)\s*(\d+)', subject, re.IGNORECASE)
    if not match:
        match = re.search(r'(\d+)', subject)
    return match.group(1) if match else "unknown"


def normalize_audio(input_path):
    """
    Normalizes volume using EBU R128 (-16 LUFS).
    Handles .mp3 and .m4a safely using a non-destructive 'Copy-Verify-Swap' pattern.
    """
    if not os.path.exists(input_path):
        print(f"❌ Source file missing: {input_path}")
        return False

    print(f"🔊 Normalizing: {os.path.basename(input_path)} using safe normalization...")
    
    # 1. Determine extension and appropriate codec
    file_ext = os.path.splitext(input_path)[1].lower()
    
    # Map extensions to valid codecs
    # .m4a needs aac, .mp3 needs libmp3lame
    codec_map = {
        '.m4a': 'aac',
        '.mp3': 'libmp3lame',
        '.wav': 'pcm_s16le'
    }
    target_codec = codec_map.get(file_ext, 'libmp3lame')
    
    # 2. Use a temporary directory for the output to prevent destructive loss
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_output = os.path.join(tmp_dir, f"norm_{os.path.basename(input_path)}")

        # Configure the normalizer
        norm = FFmpegNormalize(
            normalization_type='ebu',
            target_level=-16,
            audio_codec=target_codec,
            extra_output_options=['-b:a', '320k'] if target_codec != 'aac' else ['-b:a', '192k'],
            print_stats=False,
            overwrite=True
        )
        
        try:
            # Create MediaFile and run
            media_file = MediaFile(norm, input_path, temp_output)
            norm.media_files.append(media_file)
            norm.run_normalization()
            
            # 3. VERIFICATION: Ensure output exists and is not an empty file
            if os.path.exists(temp_output) and os.path.getsize(temp_output) > 0:
                # 4. SWAP: Only now do we overwrite the original source
                # Using shutil.move across potential file system boundaries
                shutil.move(temp_output, input_path)
                print(f"✅ Success: {os.path.basename(input_path)}")
                return True
            else:
                print(f"⚠️ Verification failed: Output for {input_path} was empty.")
                return False
                
        except Exception as e:
            print(f"❌ Normalization failed for {os.path.basename(input_path)}")
            print(f"   Reason: {e}")
            # Source file is safe because we only worked on the temp copy
            return False


def prepare_and_prompt(subject,attachments,body):
    print("🧠 Gemini is analyzing...")
    prompt = f"""
    Extract the 'Sonic Twist' newsletter into a JSON object.
    SUBJECT: {subject}
    ATTACHMENTS AVAILABLE: {attchments}
    BODY: {body}

    SCHEMA: 
    {{ 
    "issue_number": int, 
    "issue_image": "string",
    "tracks": [ 
        {{ 
        "track_num": int, 
        "title": "string", 
        "credits": "string", 
        "lyrics": "string", 
        "audio_file": "slugified_filename_here",
        "track_image": "image_file"
        }}
    ] 
    }}
    """
    
    # Call Gemini with the new retry logic
    structured_data = ask_gemini_with_retry(prompt)

    return structured_data


def is_already_downloaded(uid, registry_path="downloaded_uids.json"):
    if not os.path.exists(registry_path):
        return False
    with open(registry_path, "r") as f:
        processed_uids = json.load(f)
    return str(uid) in processed_uids

def mark_as_downloaded(uid, registry_path="downloaded_uids.json"):
    processed_uids = []
    if os.path.exists(registry_path):
        with open(registry_path, "r") as f:
            processed_uids = json.load(f)
    
    if str(uid) not in processed_uids:
        processed_uids.append(str(uid))
        with open(registry_path, "w") as f:
            json.dump(processed_uids, f)