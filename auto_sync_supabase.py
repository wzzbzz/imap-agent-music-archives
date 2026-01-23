#!/usr/bin/env python3
"""
Auto-sync newly processed releases to Supabase.
Run this after your email processing cron job.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from supabase_sync import sync_release_to_supabase, ensure_collection_exists, COLLECTIONS


def sync_recent_releases(hours=24):
    """
    Sync releases that were modified in the last N hours.
    
    Args:
        hours: Only sync releases modified in the last N hours
    """
    cutoff_time = datetime.now().timestamp() - (hours * 3600)
    base_path = Path(__file__).parent / "archives"
    
    synced_count = 0
    
    for collection_id, collection_config in COLLECTIONS.items():
        collection_path = base_path / collection_id
        
        if not collection_path.exists():
            continue
        
        # Ensure collection exists in Supabase
        ensure_collection_exists(collection_id, collection_config)
        
        # Find recently modified releases
        release_type = collection_config['release_type']
        release_pattern = f"{release_type}_"
        
        for release_dir in collection_path.iterdir():
            if not release_dir.is_dir() or not release_dir.name.startswith(release_pattern):
                continue
            
            # Check if metadata.json was recently modified
            metadata_file = release_dir / "metadata.json"
            if not metadata_file.exists():
                continue
            
            if metadata_file.stat().st_mtime < cutoff_time:
                continue
            
            # Sync this release
            print(f"\n📤 Syncing {collection_id}/{release_dir.name}...")
            success = sync_release_to_supabase(
                collection_id=collection_id,
                release_dir=release_dir,
                release_type=release_type
            )
            
            if success:
                synced_count += 1
    
    print(f"\n✅ Synced {synced_count} releases to Supabase")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Auto-sync recent releases to Supabase")
    parser.add_argument(
        '--hours',
        type=int,
        default=24,
        help='Sync releases modified in the last N hours (default: 24)'
    )
    
    args = parser.parse_args()
    
    print(f"🔍 Looking for releases modified in the last {args.hours} hours...")
    sync_recent_releases(hours=args.hours)
