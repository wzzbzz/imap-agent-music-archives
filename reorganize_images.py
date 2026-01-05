#!/usr/bin/env python3
"""
Reorganize release images into images/ folders.
Creates an images/ folder in each release and moves all image files there.
"""

import json
import shutil
from pathlib import Path

# Base path for archives
BASE_PATH = Path("/Users/jamespwilliams/Projects/python/email_archiving")

# Collection configurations
COLLECTIONS = [
    {
        "id": "sonic_twist",
        "folder": "sonic_twist_archives",
        "release_pattern": "Issue_",
    },
    {
        "id": "even_more_cake",
        "folder": "even_more_cake_archives",
        "release_pattern": "Volume_",
    },
    {
        "id": "off_the_grid",
        "folder": "off_the_grid_archives",
        "release_pattern": "Volume_",
    }
]

# Image extensions to look for
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}


def reorganize_collection_images(collection: dict):
    """Reorganize images for a single collection."""
    collection_path = BASE_PATH / collection["folder"]
    
    if not collection_path.exists():
        print(f"⚠️  Collection not found: {collection_path}")
        return
    
    # Find all release folders
    release_folders = [
        f for f in collection_path.iterdir() 
        if f.is_dir() and f.name.startswith(collection["release_pattern"])
    ]
    
    print(f"\n📁 Processing {collection['id']}: {len(release_folders)} releases")
    
    for release_folder in sorted(release_folders):
        # Find all image files in the release root AND audio folder
        image_files = [
            f for f in release_folder.iterdir()
            if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
        ]
        
        # Also check audio folder for images
        audio_folder = release_folder / "audio"
        if audio_folder.exists():
            audio_images = [
                f for f in audio_folder.iterdir()
                if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
            ]
            image_files.extend(audio_images)
        
        if not image_files:
            continue
        
        # Create images directory
        images_dir = release_folder / "images"
        images_dir.mkdir(exist_ok=True)
        
        # Move images
        moved_count = 0
        for image_file in image_files:
            dest = images_dir / image_file.name
            if not dest.exists():
                shutil.move(str(image_file), str(dest))
                moved_count += 1
        
        if moved_count > 0:
            print(f"  ✓ {release_folder.name}: Moved {moved_count} image(s) to images/")
        
        # Update metadata.json if it has release_image field
        metadata_file = release_folder / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Check for issue_image or release_image
            image_field = 'issue_image' if 'issue_image' in metadata else 'release_image'
            old_image = metadata.get(image_field)
            
            if old_image and not old_image.startswith('images/'):
                # Update path to point to images/ folder
                new_image = f"images/{old_image}"
                metadata[image_field] = new_image
                
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=4, ensure_ascii=False)
                
                print(f"    → Updated metadata.json: {old_image} -> {new_image}")


def main():
    """Reorganize images for all collections."""
    print("🖼️  Reorganizing Release Images...")
    
    for collection in COLLECTIONS:
        reorganize_collection_images(collection)
    
    print("\n✅ Image reorganization complete!")
    print("\n📝 Next steps:")
    print("  1. Run generate_manifests.py to update manifest files")
    print("  2. Update symlinks in archival-radio/public if needed")


if __name__ == "__main__":
    main()
