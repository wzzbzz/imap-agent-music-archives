#!/usr/bin/env python3
"""
Process a single email by Message-ID for any workflow.
Handles both regular workflows and single-release workflows (like Mixed Nuts).
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from workflows import get_workflow
from email_processor import EmailProcessor
from imap_utils import fetch_emails
from utils import clean_text, sanitize_for_json, slugify_filename
from attachment_handlers import get_handler


def get_next_track_number(metadata_file: Path) -> int:
    """Get the next track number from existing metadata."""
    if not metadata_file.exists():
        return 1
    
    with open(metadata_file, 'r') as f:
        metadata = json.load(f)
    
    return len(metadata.get('tracks', [])) + 1


def process_by_message_id(workflow_name: str, message_id: str):
    """
    Process a specific email by its Message-ID.
    Handles single-release mode automatically.
    """
    workflow = get_workflow(workflow_name)
    base_dir = Path(workflow.base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🔍 Looking for email with Message-ID: {message_id}")
    
    # Fetch the specific email
    imap_args = workflow.to_imap_args()
    imap_args['message_id'] = message_id
    
    found = False
    for msg in fetch_emails(imap_args):
        found = True
        print(f"\n✅ Found email: {msg.subject}")
        
        try:
            if workflow.single_release_mode:
                # SINGLE RELEASE MODE (e.g., Mixed Nuts)
                process_single_release_email(msg, workflow)
            else:
                # REGULAR MODE
                processor = EmailProcessor(workflow)
                processor.process_single_email(msg, force=True)
                processor._mark_processed(msg.uid)
            
            print(f"\n✅ Successfully processed!")
            return True
            
        except Exception as e:
            print(f"\n❌ Error processing: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    if not found:
        print(f"\n❌ No email found with Message-ID: {message_id}")
        return False


def process_single_release_email(msg, workflow):
    """Process an email for a single-release workflow."""
    base_dir = Path(workflow.base_dir)
    release_dir = base_dir / workflow.single_release_name
    audio_dir = release_dir / "audio"
    images_dir = release_dir / "images"
    metadata_file = release_dir / "metadata.json"
    
    # Create directories
    audio_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)
    
    # Process attachments
    attachment_metadata = []
    extracted_text = {}
    
    for att in msg.attachments:
        result = process_attachment(att, release_dir, extracted_text, workflow)
        if result:
            attachment_metadata.extend(result)
    
    # Load or create metadata
    if metadata_file.exists():
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        print(f"📝 Appending to existing release with {len(metadata.get('tracks', []))} tracks")
    else:
        metadata = {
            "release_number": 1,
            "tracks": []
        }
        print(f"📝 Creating new release")
    
    # Add new track(s)
    for att_meta in attachment_metadata:
        if att_meta.get('slugified', '').endswith(('.mp3', '.m4a', '.wav')):
            audio_path = audio_dir / att_meta['slugified']
            duration = get_duration(audio_path)
            
            track = {
                "track_num": len(metadata['tracks']) + 1,
                "title": clean_text(msg.subject),
                "credits": msg.from_,
                "date_written": str(msg.date),
                "lyrics": extracted_text.get('lyrics', ''),
                "audio_file": att_meta['slugified'],
                "track_image": None,
                "duration": duration
            }
            
            metadata['tracks'].append(track)
            print(f"  ✓ Added track #{track['track_num']}: {track['title']}")
    
    # Save metadata
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=4)
    
    print(f"✅ Release now has {len(metadata['tracks'])} total tracks")


def process_attachment(att, release_dir, extracted_text, workflow):
    """Process a single attachment."""
    orig_name = clean_text(att.filename)
    
    # Determine target directory
    if is_image(orig_name):
        target_dir = release_dir / "images"
    else:
        target_dir = release_dir / "audio"
    
    # Find matching processor
    for processor_config in workflow.attachment_processors:
        if matches_pattern(orig_name, processor_config.file_patterns):
            handler = get_handler(processor_config.handler)
            return handler(
                attachment=att,
                target_dir=target_dir,
                extracted_text=extracted_text,
                options=processor_config.options,
                workflow=workflow
            )
    
    # No processor - save as-is
    slugged_name = slugify_filename(orig_name)
    file_path = target_dir / slugged_name
    with open(file_path, 'wb') as f:
        f.write(att.payload)
    return [{"original": orig_name, "slugified": slugged_name}]


def is_image(filename: str) -> bool:
    """Check if filename is an image."""
    exts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']
    return any(filename.lower().endswith(ext) for ext in exts)


def matches_pattern(filename: str, patterns):
    """Check if filename matches any pattern."""
    import fnmatch
    return any(fnmatch.fnmatch(filename.lower(), p.lower()) for p in patterns)


def get_duration(audio_path: Path) -> int:
    """Get audio duration in seconds."""
    try:
        from mutagen.mp3 import MP3
        audio = MP3(str(audio_path))
        return int(audio.info.length)
    except:
        return 0


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Process a specific email by Message-ID"
    )
    parser.add_argument('workflow', help='Workflow name (e.g., mixed_nuts, sonic_twist)')
    parser.add_argument('message_id', help='Message-ID from email header')
    
    args = parser.parse_args()
    
    success = process_by_message_id(args.workflow, args.message_id)
    
    if success:
        workflow = get_workflow(args.workflow)
        if workflow.single_release_mode:
            print(f"\n💡 Sync to Supabase:")
            print(f"   python supabase_sync.py {args.workflow} --release {workflow.single_release_name}")
    
    sys.exit(0 if success else 1)
