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
from utils import clean_text, sanitize_for_json


def process_by_message_id(workflow_name: str, message_id: str):
    """
    Process a specific email by its Message-ID.
    Handles single-release mode automatically.
    """
    workflow = get_workflow(workflow_name)
    
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
    """
    Process an email for a single-release workflow.
    Generates LLM metadata for the new track(s), then appends to existing release.
    """
    from llm_metadata import generate_metadata_for_release
    
    base_dir = Path(workflow.base_dir)
    release_dir = base_dir / workflow.single_release_name
    audio_dir = release_dir / "audio"
    images_dir = release_dir / "images"
    main_metadata_file = release_dir / "metadata.json"
    
    # Create temporary directory for this new email
    temp_dir = release_dir / f"_temp_{msg.uid}"
    temp_audio_dir = temp_dir / "audio"
    temp_images_dir = temp_dir / "images"
    temp_audio_dir.mkdir(parents=True, exist_ok=True)
    temp_images_dir.mkdir(parents=True, exist_ok=True)
    
    # Process attachments into temp directory
    processor = EmailProcessor(workflow)
    attachment_metadata = []
    extracted_text = {}
    
    for att in msg.attachments:
        result = processor._process_attachment(att, temp_dir, extracted_text)
        if result:
            attachment_metadata.extend(result)
    
    # Save raw email data
    raw_data = {
        "uid": msg.uid,
        "message_id": msg.obj.get('Message-ID'),
        "subject": clean_text(msg.subject),
        "body": sanitize_for_json(msg.text or msg.html),
        "date": str(msg.date),
        "from": msg.from_,
        "to": msg.to,
        "attachments": attachment_metadata,
        **extracted_text
    }
    
    temp_raw_file = temp_dir / "raw.json"
    with open(temp_raw_file, 'w') as f:
        json.dump(raw_data, f, indent=4)
    
    # Generate LLM metadata for this email
    print(f"🧠 Generating track metadata with {workflow.metadata_llm_provider.upper()}...")
    
    success = generate_metadata_for_release(
        release_dir=temp_dir,
        provider=workflow.metadata_llm_provider,
        schema=workflow.metadata_schema
    )
    
    if not success:
        print(f"⚠️  Metadata generation failed")
        import shutil
        shutil.rmtree(temp_dir)
        return
    
    # Add durations to new tracks
    processor._add_track_durations(temp_dir)
    
    # Load the newly generated metadata
    temp_metadata_file = temp_dir / "metadata.json"
    with open(temp_metadata_file, 'r') as f:
        new_metadata = json.load(f)
    
    # Load or create main metadata
    if main_metadata_file.exists():
        with open(main_metadata_file, 'r') as f:
            main_metadata = json.load(f)
        print(f"📝 Appending to existing release with {len(main_metadata.get('tracks', []))} tracks")
    else:
        main_metadata = {
            "release_number": 1,
            "tracks": []
        }
        print(f"📝 Creating new release")
    
    # Move files from temp to main directories
    audio_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)
    
    import shutil
    for file in temp_audio_dir.iterdir():
        shutil.move(str(file), str(audio_dir / file.name))
    for file in temp_images_dir.iterdir():
        shutil.move(str(file), str(images_dir / file.name))
    
    # Append new tracks with updated track numbers
    for track in new_metadata.get('tracks', []):
        track['track_num'] = len(main_metadata['tracks']) + 1
        main_metadata['tracks'].append(track)
        print(f"  ✓ Added track #{track['track_num']}: {track.get('title', 'Unknown')}")
    
    # Save updated main metadata
    with open(main_metadata_file, 'w') as f:
        json.dump(main_metadata, f, indent=4)
    
    # Clean up temp directory
    shutil.rmtree(temp_dir)
    
    print(f"✅ Release now has {len(main_metadata['tracks'])} total tracks")


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
        if workflow.collection_type in ("playlist", "named_release"):
            if workflow.collection_type == "playlist":
                release_arg = f"--release {workflow.single_release_name}"
            else:
                release_arg = "--all"
            print(f"\n💡 Sync to Supabase:")
            print(f"   python supabase_sync.py {args.workflow} {release_arg}")
    
    sys.exit(0 if success else 1)
