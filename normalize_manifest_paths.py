#!/usr/bin/env python3
"""
Postprocessor to normalize image paths in manifest.json files.

Ensures all release_image paths follow the format:
  archives/{collection_id}/Issue_X/images/filename.jpg

Usage:
  python normalize_manifest_paths.py                    # Process all collections
  python normalize_manifest_paths.py sonic_twist        # Process specific collection
"""

import json
import sys
from pathlib import Path


def normalize_image_path(release_image: str | None, collection_id: str, release_number: int, release_type: str) -> str | None:
    """
    Normalize a release image path to the standard format.
    
    Args:
        release_image: Original image path (may be None)
        collection_id: Collection ID (e.g., "sonic_twist")
        release_number: Release number
        release_type: Release type (e.g., "Issue", "Volume")
        
    Returns:
        Normalized path or None if no image
    """
    if not release_image:
        return None
    
    # Extract just the filename from the path
    filename = Path(release_image).name
    
    # Build the standardized path
    # Format: archives/{collection_id}/{ReleaseType}_{number}/images/{filename}
    normalized = f"archives/{collection_id}/{release_type}_{release_number}/images/{filename}"
    
    return normalized


def process_manifest(manifest_path: Path) -> dict:
    """
    Process a manifest file and normalize all image paths.
    
    Returns dict with counts of changes made.
    """
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    collection_id = manifest['collection_id']
    changes = {
        'total': 0,
        'normalized': 0,
        'unchanged': 0,
        'null': 0
    }
    
    for release in manifest['releases']:
        changes['total'] += 1
        original = release.get('release_image')
        
        if original is None:
            changes['null'] += 1
            continue
        
        normalized = normalize_image_path(
            original,
            collection_id,
            release['release_number'],
            release['release_type']
        )
        
        if normalized != original:
            release['release_image'] = normalized
            changes['normalized'] += 1
            print(f"  Issue {release['release_number']}: {original} -> {normalized}")
        else:
            changes['unchanged'] += 1
    
    # Write back the normalized manifest
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    return changes


def main():
    archives_dir = Path(__file__).parent / 'archives'
    
    # Get collection to process (if specified)
    target_collection = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Find all manifest files
    if target_collection:
        manifest_files = [archives_dir / target_collection / 'manifest.json']
    else:
        manifest_files = list(archives_dir.glob('*/manifest.json'))
    
    total_changes = 0
    
    for manifest_path in manifest_files:
        if not manifest_path.exists():
            print(f"Warning: {manifest_path} does not exist")
            continue
        
        collection_name = manifest_path.parent.name
        print(f"\nProcessing {collection_name}...")
        
        changes = process_manifest(manifest_path)
        total_changes += changes['normalized']
        
        print(f"  Total releases: {changes['total']}")
        print(f"  Normalized: {changes['normalized']}")
        print(f"  Unchanged: {changes['unchanged']}")
        print(f"  No image: {changes['null']}")
    
    print(f"\n✓ Complete! Normalized {total_changes} paths across {len(manifest_files)} collections")


if __name__ == '__main__':
    main()
