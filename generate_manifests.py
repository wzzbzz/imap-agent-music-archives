#!/usr/bin/env python3
"""
Generate manifest files for each collection.
Each manifest lists all releases in that collection.
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List

# Base path for archives - defaults to script directory
BASE_PATH = Path(__file__).parent.resolve()

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


def generate_collection_manifest(collection: Dict, base_path: Path = BASE_PATH) -> Dict:
    """Generate a manifest for a single collection."""
    collection_path = base_path / collection["folder"]
    
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

        # ensure that release_image is in format ()
        
        # Build full path for release image (similar to audio files)
        if release_image:
            release_image = re.sub("images/","",release_image)
            release_image = f"{collection['folder']}/{release_folder.name}/images/{release_image}"
        
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
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate collection manifests")
    parser.add_argument(
        '--base-path',
        type=Path,
        default=BASE_PATH,
        help=f"Base path for archives (default: script directory)"
    )
    args = parser.parse_args()
    
    base_path = args.base_path
    
    print("📋 Generating Collection Manifests...")
    print(f"📍 Base path: {base_path}")
    
    for collection in COLLECTIONS:
        print(f"\n📁 Processing {collection['id']}...")
        
        manifest = generate_collection_manifest(collection, base_path)
        
        if not manifest:
            continue
        
        collection_dir = base_path / collection["folder"]

        print(collection_dir)

        collection_dir.mkdir(parents=True, exist_ok=True)
        
        manifest_path = collection_dir / "manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        print(f"  ✅ Generated manifest: {manifest['total_releases']} releases")
        print(f"  📍 {manifest_path}")
    
    print("\n✅ All manifests generated!")


if __name__ == "__main__":
    main()
