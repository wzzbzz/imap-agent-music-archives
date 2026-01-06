#!/usr/bin/env python3
"""
Generate a master track registry from all archive folders.
Creates tracks.json with canonical track data.
"""

import json
import os
from pathlib import Path
from typing import Dict, List

# Base path for archives
BASE_PATH = Path("/Users/jamespwilliams/Ampelos/greenhouse/email_archiving")

# Collection configurations
COLLECTIONS = [
    {
        "id": "sonic_twist",
        "folder": "archives/sonic_twist",
        "release_pattern": "Issue_",
        "release_type": "Issue"
    },
    {
        "id": "even_more_cake",
        "folder": "archives/even_more_cake",
        "release_pattern": "Volume_",
        "release_type": "Volume"
    },
    {
        "id": "off_the_grid",
        "folder": "archives/off_the_grid",
        "release_pattern": "Volume_",
        "release_type": "Volume"
    }
]


def generate_track_id(audio_file: str, collection_id: str) -> str:
    """
    Generate a unique track ID from audio filename.
    Example: '02_gravy_1_19.mp3' -> 'sonic_twist_gravy_1_19'
    """
    # Remove extension and leading track number
    base = audio_file.replace('.mp3', '')
    parts = base.split('_')
    
    # Remove leading numeric track number if present
    if parts[0].isdigit():
        parts = parts[1:]
    
    track_name = '_'.join(parts)
    return f"{collection_id}_{track_name}"


def scan_collection(collection: Dict) -> Dict[str, Dict]:
    """
    Scan a collection folder and extract all track metadata.
    Returns dict of track_id -> track_data
    """
    tracks = {}
    collection_path = BASE_PATH / collection["folder"]
    
    if not collection_path.exists():
        print(f"⚠️  Collection not found: {collection_path}")
        return tracks
    
    # Find all release folders
    release_folders = [
        f for f in collection_path.iterdir() 
        if f.is_dir() and f.name.startswith(collection["release_pattern"])
    ]
    
    print(f"\n📁 Scanning {collection['id']}: {len(release_folders)} releases")
    
    for release_folder in sorted(release_folders):
        metadata_file = release_folder / "metadata.json"
        
        if not metadata_file.exists():
            print(f"  ⚠️  No metadata: {release_folder.name}")
            continue
        
        # Load metadata
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        release_num = metadata.get('issue_number') or metadata.get('release_number')
        
        # Process each track
        for track in metadata.get('tracks', []):
            audio_file = track.get('audio_file')
            print(audio_file)
            
            if not audio_file:
                continue
            
            # Generate unique track ID
            track_id = generate_track_id(audio_file, collection['id'])
            
            # Build audio path relative to public folder
            audio_path = f"{collection['folder']}/{release_folder.name}/audio/{audio_file}"
            
            # Build track image path if it exists
            track_image = track.get('track_image')
            if track_image:
                track_image_path = f"{collection['folder']}/{release_folder.name}/images/{track_image}"
            else:
                track_image_path = None
            
            # Check for duplicate track IDs
            if track_id in tracks:
                print(f"  ⚠️  Duplicate track ID: {track_id}")
                # Add release number to make unique
                track_id = f"{track_id}_r{release_num}"
            
            # Store track data
            tracks[track_id] = {
                "id": track_id,
                "title": track.get('title', ''),
                "artist": track.get('credits', ''),
                "date_written": track.get('date_written', ''),
                "audio_file": audio_path,
                "track_image": track_image_path,
                "duration": track.get('duration', 0),
                "lyrics": track.get('lyrics', ''),
                "collection_id": collection['id'],
                "first_appearance": f"{collection['release_type']} {release_num}"
            }
        
        print(f"  ✓ {release_folder.name}: {len(metadata.get('tracks', []))} tracks")
    
    return tracks


def main():
    """Generate the master track registry."""
    print("🎵 Generating Track Registry...")
    
    all_tracks = {}
    
    # Scan each collection
    for collection in COLLECTIONS:
        collection_tracks = scan_collection(collection)
        all_tracks.update(collection_tracks)
    
    # Create output structure
    registry = {
        "tracks": all_tracks,
        "metadata": {
            "total_tracks": len(all_tracks),
            "collections": [c["id"] for c in COLLECTIONS],
            "generated": "2025-01-03"
        }
    }
    
    # Write to archival-radio public folder
    output_path = BASE_PATH / "archives" / "tracks.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Generated tracks.json: {len(all_tracks)} total tracks")
    print(f"📍 Location: {output_path}")
    
    # Print summary by collection
    print("\n📊 Summary:")
    for collection in COLLECTIONS:
        count = sum(1 for t in all_tracks.values() if t['collection_id'] == collection['id'])
        print(f"  {collection['id']}: {count} tracks")


if __name__ == "__main__":
    main()
