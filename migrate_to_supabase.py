#!/usr/bin/env python3
"""
Migrate existing JSON archives to Supabase.
Reads collections.json, tracks.json, and manifests, then uploads to Supabase.
"""

import json
import os
from pathlib import Path
from supabase import create_client, Client
from typing import Dict, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in environment")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Paths
BASE_PATH = Path(__file__).parent
ARCHIVES_PATH = BASE_PATH / "archives"


def generate_track_id(audio_file: str, collection_id: str) -> str:
    """Generate a unique track ID from audio filename."""
    base = audio_file.replace('.mp3', '')
    parts = base.split('_')
    if parts[0].isdigit():
        parts = parts[1:]
    track_name = '_'.join(parts)
    return f"{collection_id}_{track_name}"


def migrate_collections():
    """Migrate collections.json to Supabase."""
    print("\n📁 Migrating Collections...")
    
    collections_file = ARCHIVES_PATH / "collections.json"
    if not collections_file.exists():
        print("  ⚠️  collections.json not found")
        return
    
    with open(collections_file, 'r') as f:
        data = json.load(f)
    
    collections = data.get('collections', [])
    
    for collection in collections:
        db_collection = {
            'id': collection['id'],
            'name': collection['name'],
            'artist': collection['artist'],
            'release_type': collection['releaseType'],
            'color': collection['color'],
            'description': collection['description'],
            'active': collection.get('active', True),
            'is_virtual': collection.get('isVirtual', False)
        }
        
        result = supabase.table('collections').upsert(db_collection).execute()
        print(f"  ✓ {collection['name']}")
    
    print(f"  ✅ Migrated {len(collections)} collections")


def migrate_releases_and_tracks():
    """Migrate releases from manifests and tracks from tracks.json."""
    print("\n📀 Migrating Releases and Tracks...")
    
    # Load tracks.json
    tracks_file = ARCHIVES_PATH / "tracks.json"
    if not tracks_file.exists():
        print("  ⚠️  tracks.json not found")
        return
    
    with open(tracks_file, 'r') as f:
        tracks_data = json.load(f)
    
    all_tracks = tracks_data.get('tracks', {})
    
    # Get collections to iterate through
    collections_result = supabase.table('collections').select('id').execute()
    collections = [c['id'] for c in collections_result.data if not c.get('is_virtual')]
    
    release_id_map = {}
    track_order_map = {}
    
    # First pass: insert releases and build track order map from metadata files
    for collection_id in collections:
        print(f"\n  📁 Processing {collection_id}...")
        
        manifest_file = ARCHIVES_PATH / collection_id / "manifest.json"
        if not manifest_file.exists():
            print(f"    ⚠️  No manifest found")
            continue
        
        with open(manifest_file, 'r') as f:
            manifest = json.load(f)
        
        releases = manifest.get('releases', [])
        release_type = manifest.get('release_type', 'Issue')
        
        for release in releases:
            db_release = {
                'collection_id': collection_id,
                'release_number': release['release_number'],
                'release_type': release['release_type'],
                'release_date': release.get('release_date'),
                'release_image': release.get('release_image'),
                'track_count': release['track_count'],
                'total_duration': release['total_duration']
            }
            
            result = supabase.table('releases').upsert(
                db_release,
                on_conflict='collection_id,release_number'
            ).execute()
            
            if result.data:
                release_id = result.data[0]['id']
                key = (collection_id, release['release_number'])
                release_id_map[key] = release_id
            
            # Read metadata to get track ordering
            folder_name = f"{release_type}_{release['release_number']}"
            metadata_file = ARCHIVES_PATH / collection_id / folder_name / "metadata.json"
            
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    for track in metadata.get('tracks', []):
                        audio_file = track.get('audio_file')
                        track_num = track.get('track_num')
                        if audio_file and track_num:
                            track_id = generate_track_id(audio_file, collection_id)
                            track_order_map[track_id] = track_num
        
        print(f"    ✓ Inserted {len(releases)} releases")
    
    # Second pass: insert tracks with proper ordering
    print(f"\n  🎵 Inserting {len(all_tracks)} tracks...")
    track_count = 0
    
    for track_id, track in all_tracks.items():
        first_appearance = track['first_appearance']
        release_number = int(first_appearance.split()[-1])
        
        key = (track['collection_id'], release_number)
        release_id = release_id_map.get(key)
        
        # Get track order from map
        track_order = track_order_map.get(track_id)
        
        db_track = {
            'id': track_id,
            'title': track['title'],
            'artist': track.get('artist'),
            'date_written': track.get('date_written', ''),
            'lyrics': track.get('lyrics', ''),
            'audio_file': track['audio_file'],
            'track_image': track.get('track_image'),
            'duration': track['duration'],
            'collection_id': track['collection_id'],
            'release_id': release_id,
            'first_appearance': track['first_appearance'],
            'track_order': track_order
        }
        
        supabase.table('tracks').upsert(db_track).execute()
        track_count += 1
        
        if track_count % 10 == 0:
            print(f"    ... {track_count} tracks")
    
    print(f"  ✅ Migrated {track_count} tracks")


def verify_migration():
    """Verify the migration by counting records."""
    print("\n🔍 Verifying Migration...")
    
    collections = supabase.table('collections').select('id', count='exact').execute()
    print(f"  Collections: {collections.count}")
    
    releases = supabase.table('releases').select('id', count='exact').execute()
    print(f"  Releases: {releases.count}")
    
    tracks = supabase.table('tracks').select('id', count='exact').execute()
    print(f"  Tracks: {tracks.count}")
    
    print("\n✅ Migration Complete!")


def main():
    """Run the full migration."""
    print("🚀 Starting Supabase Migration...")
    print(f"📍 Base path: {BASE_PATH}")
    print(f"🔗 Supabase URL: {SUPABASE_URL}")
    
    try:
        migrate_collections()
        migrate_releases_and_tracks()
        verify_migration()
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        raise


if __name__ == "__main__":
    main()
