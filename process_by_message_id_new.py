def process_single_release_email(msg, workflow):
    """Process an email for a single-release workflow using LLM metadata."""
    base_dir = Path(workflow.base_dir)
    release_dir = base_dir / workflow.single_release_name
    audio_dir = release_dir / "audio"
    images_dir = release_dir / "images"
    metadata_file = release_dir / "metadata.json"
    temp_metadata_file = release_dir / "new_track_metadata.json"
    raw_file = release_dir / "raw.json"
    
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
    
    # Save raw email data for LLM
    raw_data = {
        "uid": msg.uid,
        "message_id": msg.obj.get('Message-ID'),
        "subject": clean_text(msg.subject),
        "body": sanitize_for_json(msg.text or msg.html),
        "date": str(msg.date),
        "from": msg.from_,
        "attachments": attachment_metadata,
        **extracted_text
    }
    
    with open(temp_metadata_file, 'w') as f:
        json.dump(raw_data, f, indent=4)
    
    # Generate metadata using LLM
    print(f"🧠 Generating track metadata with LLM...")
    try:
        from llm_metadata import generate_metadata_for_release
        
        success = generate_metadata_for_release(
            release_dir=release_dir,
            provider=workflow.metadata_llm_provider,
            schema=workflow.metadata_schema,
            source_file="new_track_metadata.json"  # Use temp file instead of raw.json
        )
        
        if not success:
            print(f"⚠️  LLM metadata generation failed")
            return
        
        # Load the newly generated metadata
        with open(temp_metadata_file.replace('.json', '_generated.json'), 'r') as f:
            new_track_data = json.load(f)
        
        # Add duration to tracks
        for track in new_track_data.get('tracks', []):
            audio_file = track.get('audio_file')
            if audio_file:
                audio_path = audio_dir / audio_file
                track['duration'] = get_duration(audio_path)
        
    except Exception as e:
        print(f"⚠️  Error generating LLM metadata: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Load or create the main metadata file
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
    
    # Append new tracks, updating track_num
    for new_track in new_track_data.get('tracks', []):
        new_track['track_num'] = len(metadata['tracks']) + 1
        metadata['tracks'].append(new_track)
        print(f"  ✓ Added track #{new_track['track_num']}: {new_track.get('title', 'Unknown')}")
    
    # Save updated metadata
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=4)
    
    # Clean up temp files
    temp_metadata_file.unlink(missing_ok=True)
    Path(str(temp_metadata_file).replace('.json', '_generated.json')).unlink(missing_ok=True)
    
    print(f"✅ Release now has {len(metadata['tracks'])} total tracks")
