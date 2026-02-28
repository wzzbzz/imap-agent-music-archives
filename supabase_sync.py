#!/usr/bin/env python3
"""
Supabase Sync - Upload email archive data directly to Supabase
Replaces the need for generate_manifests.py and generate_track_registry.py
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.resolve()))
from workflows import WORKFLOWS

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in environment")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Display metadata per collection (presentation data not stored in WorkflowConfig)
COLLECTION_DISPLAY = {
    "sonic_twist": {
        "name": "Sonic Twist",
        "artist": "Jackie Puppet Band",
        "color": "#3b82f6",
        "description": "Sonic Twist newsletter archive with audio tracks and lyrics"
    },
    "even_more_cake": {
        "name": "Even More Cake",
        "artist": "Jackie Puppet Band",
        "color": "#ec4899",
        "description": "Even More Cake radio show archives"
    },
    "off_the_grid": {
        "name": "Off the Grid",
        "artist": "Jackie Puppet Band",
        "color": "#10b981",
        "description": "Off the Grid radio show archives"
    },
    "mixed_nuts": {
        "name": "Mixed Nuts",
        "artist": "Jackie Puppet Band",
        "color": "#f59e0b",
        "description": "One-off tracks and miscellaneous recordings"
    },
    "nice_threads": {
        "name": "Nice Threads",
        "artist": "Jackie Puppet Band",
        "color": "#facc15",
        "description": "Thematic, dramatic trips through the Puppetscape"
    },
}

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in environment")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def generate_track_id(audio_file: str, collection_id: str) -> str:
    """Generate a unique track ID from audio filename."""
    base = audio_file.replace('.mp3', '')
    parts = base.split('_')
    if parts[0].isdigit():
        parts = parts[1:]
    track_name = '_'.join(parts)
    return f"{collection_id}_{track_name}"


def sync_release_to_supabase(
    collection_id: str,
    release_dir: Path,
    release_type: str = "Issue"
) -> bool:
    """
    Sync a single release to Supabase.
    Reads metadata.json and uploads release + tracks.
    
    Args:
        collection_id: The collection this release belongs to
        release_dir: Path to the release directory (e.g., Issue_23)
        release_type: "Issue", "Volume", etc.
    
    Returns:
        True if successful, False otherwise
    """
    metadata_file = release_dir / "metadata.json"
    raw_file = release_dir / "raw.json"
    
    if not metadata_file.exists():
        print(f"  ⚠️  No metadata.json in {release_dir.name}")
        return False
    
    try:
        # Load metadata
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Load raw.json for release date
        release_date = None
        if raw_file.exists():
            with open(raw_file, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
                release_date = raw_data.get('date')
        
        release_num = metadata.get('issue_number') or metadata.get('release_number')
        release_image = metadata.get('issue_image') or metadata.get('release_image')
        
        # Build release image path
        if release_image:
            release_image = release_image.replace("images/", "")
            release_image = f"archives/{collection_id}/{release_dir.name}/images/{release_image}"
        
        tracks_data = metadata.get('tracks', [])
        total_duration = sum(t.get('duration', 0) for t in tracks_data)
        
        # Upsert release
        db_release = {
            'collection_id': collection_id,
            'release_number': release_num,
            'release_type': release_type,
            'release_date': release_date,
            'release_image': release_image,
            'track_count': len(tracks_data),
            'total_duration': total_duration
        }
        
        result = supabase.table('releases').upsert(
            db_release,
            on_conflict='collection_id,release_number'
        ).execute()
        
        if not result.data:
            print(f"  ⚠️  Failed to upsert release {release_num}")
            return False
        
        release_id = result.data[0]['id']
        print(f"  ✓ Release {release_num} synced (ID: {release_id})")
        
        # Upsert tracks
        for track_data in tracks_data:
            audio_file = track_data.get('audio_file')
            if not audio_file:
                continue
            
            track_id = generate_track_id(audio_file, collection_id)
            audio_path = f"archives/{collection_id}/{release_dir.name}/audio/{audio_file}"
            
            track_image = track_data.get('track_image')
            track_image_path = None
            if track_image:
                track_image_path = f"archives/{collection_id}/{release_dir.name}/images/{track_image}"
            
            db_track = {
                'id': track_id,
                'title': track_data.get('title', ''),
                'artist': track_data.get('credits'),
                'date_written': track_data.get('date_written', ''),
                'lyrics': track_data.get('lyrics', ''),
                'audio_file': audio_path,
                'track_image': track_image_path,
                'duration': track_data.get('duration', 0),
                'collection_id': collection_id,
                'release_id': release_id,
                'first_appearance': f"{release_type} {release_num}",
                'track_order': track_data.get('track_num')
            }
            
            supabase.table('tracks').upsert(db_track).execute()
        
        print(f"  ✓ {len(tracks_data)} tracks synced")
        return True
        
    except Exception as e:
        print(f"  ❌ Error syncing release: {e}")
        return False



def ensure_collection_exists(collection_id: str, collection_config: Dict) -> bool:
    """Ensure a collection exists in Supabase."""
    try:
        workflow = WORKFLOWS[collection_id]
        display = COLLECTION_DISPLAY[collection_id]

        if workflow.collection_type == "bound_volume":
            release_type = workflow.release_indicator
        elif workflow.collection_type == "playlist":
            release_type = "Track"
        elif workflow.collection_type == "named_release":
            release_type = "Release"
        else:
            release_type = "Release"

        db_collection = {
            'id': collection_id,
            'name': display['name'],
            'artist': display['artist'],
            'release_type': release_type,
            'color': display['color'],
            'description': display.get('description', ''),
            'active': True,
            'is_virtual': False
        }

        supabase.table('collections').upsert(db_collection).execute()
        return True

    except Exception as e:
        print(f"❌ Error ensuring collection exists: {e}")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Sync releases to Supabase")
    parser.add_argument('collection_id', help=f"Collection ID: {list(WORKFLOWS.keys())}")
    parser.add_argument('--release', help='Specific release folder name (e.g., Issue_23)')
    parser.add_argument('--all', action='store_true', help='Sync all releases in collection')

    args = parser.parse_args()

    if args.collection_id not in WORKFLOWS:
        print(f"Unknown collection: {args.collection_id}")
        print(f"Available: {list(WORKFLOWS.keys())}")
        exit(1)

    if args.collection_id not in COLLECTION_DISPLAY:
        print(f"❌ No display config for '{args.collection_id}' — add it to COLLECTION_DISPLAY")
        exit(1)

    workflow = WORKFLOWS[args.collection_id]

    if workflow.collection_type == "bound_volume":
        release_type = workflow.release_indicator
        release_pattern = f"{release_type}_"
    elif workflow.collection_type == "playlist":
        release_type = "Track"
        release_pattern = workflow.single_release_name
    elif workflow.collection_type == "named_release":
        release_type = "Release"
        release_pattern = None
    else:
        release_type = "Release"
        release_pattern = None

    # Ensure collection exists in Supabase
    ensure_collection_exists(args.collection_id, COLLECTION_DISPLAY[args.collection_id])

    base_path = Path(__file__).parent / workflow.base_dir

    if not base_path.exists():
        print(f"Collection directory not found: {base_path}")
        exit(1)

    if args.release:
        release_dir = base_path / args.release
        if not release_dir.exists():
            print(f"Release directory not found: {release_dir}")
            exit(1)
        print(f"📤 Syncing {args.release} to Supabase...")
        sync_release_to_supabase(args.collection_id, release_dir, release_type)

    elif args.all:
        if workflow.collection_type == "named_release":
            release_folders = sorted([f for f in base_path.iterdir() if f.is_dir()])
        elif release_pattern:
            release_folders = sorted([
                f for f in base_path.iterdir()
                if f.is_dir() and f.name.startswith(release_pattern)
            ])
        else:
            release_folders = []

        print(f"📤 Syncing {len(release_folders)} releases to Supabase...")
        for release_dir in release_folders:
            sync_release_to_supabase(args.collection_id, release_dir, release_type)
        print(f"\n✅ Sync complete!")

    else:
        print("Specify either --release FOLDER or --all")
        exit(1)
