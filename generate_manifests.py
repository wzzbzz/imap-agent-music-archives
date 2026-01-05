#!/usr/bin/env python3
"""
Generate manifest files for each collection.
Each manifest lists all releases in that collection.
"""

import json
from pathlib import Path
from typing import Dict, List

# Base path for archives
BASE_PATH = Path("/Users/jamespwilliams/Projects/python/email_archiving")

# Collection configurations
COLLECTIONS = [
    {
        "id": "sonic_twist",
        "folder": "sonic_twist_archives",
        "release_pattern": "Issue_",
        "release_type": "Issue"
    },
    {
        "id": "even_more_cake",
        "folder": "even_more_cake_archives",
        "release_pattern": "Volume_",
        "release_type": "Volume"
    },
    {
        "id": "off_the_grid",
        "folder": "off_the_grid_archives",
        "release_pattern": "Volume_",
        "release_type": "Volume"
    }
]


def generate_collection_manifest(collection: Dict) -> Dict:
    """Generate a manifest for a single collection."""
    collection_path = BASE_PATH / collection["folder"]
    
    if not collection_path.exists():
        print(f"⚠️  Collection not found: {collection_path}")
        return None
    
    release_folders = [
        f for f in collection_path.iterdir() 
        if f.is_dir() and f.name.startswith(collection["release_pattern"])
    ]
    
    releases = []
    
    for release_folder in sorted(release_folders):
        metadata_file = release_folder / "metadata.json"
        raw_file = release_folder / "raw.json"
        
        if not metadata_file.exists():
            print(f"  ⚠️  No metadata: {release_folder.name}")
            continue
        
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Load raw.json to get release date
        release_date = None
        if raw_file.exists():
            with open(raw_file, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
                release_date = raw_data.get('date')
        
        release_num = metadata.get('issue_number') or metadata.get('release_number')
        release_image = metadata.get('issue_image') or metadata.get('release_image')
        
        # Build full path for release image (similar to audio files)
        if release_image:
            release_image = f"{collection['folder']}/{release_folder.name}/{release_image}"
        
        tracks = metadata.get('tracks', [])
        
        release_info = {
            "release_number": release_num,
            "release_type": collection["release_type"],
            "release_date": release_date,
            "release_image": release_image,
            "track_count": len(tracks),
            "total_duration": sum(t.get('duration', 0) for t in tracks),
            "data_file": f"{collection['id']}/{collection['release_type'].lower()}-{release_num}.json"
        }
        
        releases.append(release_info)
    
    manifest = {
        "collection_id": collection["id"],
        "release_type": collection["release_type"],
        "total_releases": len(releases),
        "releases": releases
    }
    
    return manifest


def main():
    """Generate manifest files for all collections."""
    print("📋 Generating Collection Manifests...")
    
    for collection in COLLECTIONS:
        print(f"\n📁 Processing {collection['id']}...")
        
        manifest = generate_collection_manifest(collection)
        
        if not manifest:
            continue
        
        collection_dir = BASE_PATH / "archival-radio" / "public" / "data" / collection["id"]
        collection_dir.mkdir(parents=True, exist_ok=True)
        
        manifest_path = collection_dir / "manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        print(f"  ✅ Generated manifest: {manifest['total_releases']} releases")
        print(f"  📍 {manifest_path}")
    
    print("\n✅ All manifests generated!")


if __name__ == "__main__":
    main()
