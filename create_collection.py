#!/usr/bin/env python3
"""
Collection Manager - Easy tool to create and manage collections
"""

import json
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from supabase_sync import ensure_collection_exists, COLLECTIONS
from workflows import WorkflowConfig, AttachmentProcessor, WORKFLOWS


def create_collection(
    collection_id: str,
    name: str,
    release_type: str = "Track",
    color: str = "#8b5cf6",  # Purple default
    description: str = "",
):
    """
    Create a new collection in both Supabase and the workflow system.
    
    Args:
        collection_id: Unique ID (e.g., 'mixed_nuts')
        name: Display name (e.g., 'Mixed Nuts')
        release_type: 'Track', 'Issue', 'Volume', etc.
        color: Hex color code
        description: Description of the collection
    """
    print(f"\n🆕 Creating collection: {name}")
    
    # 1. Create in Supabase
    collection_config = {
        'name': name,
        'artist': 'Jackie Puppet Band',
        'release_type': release_type,
        'color': color,
        'description': description
    }
    
    success = ensure_collection_exists(collection_id, collection_config)
    if not success:
        print("❌ Failed to create collection in Supabase")
        return False
    
    print(f"✅ Created in Supabase")
    
    # 2. Add to COLLECTIONS dict in supabase_sync.py
    print(f"📝 To persist this collection, add to supabase_sync.py COLLECTIONS:")
    print(f"""
    "{collection_id}": {{
        "name": "{name}",
        "artist": "Jackie Puppet Band",
        "release_type": "{release_type}",
        "color": "{color}",
        "description": "{description}"
    }},
""")
    
    # 3. Create workflow configuration
    print(f"\n📝 To enable email processing, add to workflows.py:")
    workflow_template = f'''
{collection_id.upper()}_WORKFLOW = WorkflowConfig(
    name="{collection_id}",
    description="{description}",
    base_dir="archives/{collection_id}",
    folder_pattern="{release_type}_{{number}}",
    
    sender="alvyhall@aol.com",
    subject_filter="{name}",  # Adjust as needed
    
    release_number_pattern=r'(?:{release_type}|#)\\s*(\\d+)',
    release_indicator="{release_type}",
    
    attachment_processors=[
        AttachmentProcessor(
            name="zip_extractor",
            file_patterns=["*.zip"],
            handler="process_zip_attachment",
        ),
        AttachmentProcessor(
            name="audio_normalizer",
            file_patterns=["*.mp3", "*.m4a", "*.wav"],
            handler="normalize_audio",
            options={{"target_lufs": -16.0, "bitrate": "320k"}}
        ),
        AttachmentProcessor(
            name="image_saver",
            file_patterns=["*.jpg", "*.jpeg", "*.png", "*.gif"],
            handler="save_image",
        ),
        AttachmentProcessor(
            name="lyrics_extractor",
            file_patterns=["*.docx"],
            handler="extract_docx_text",
            options={{"field_name": "lyrics"}}
        ),
    ],
    
    normalize_audio=True,
    audio_output_format="mp3",
    extract_lyrics_from_docx=True,
    merge_fragments=False,
)

# Add to registry
WORKFLOWS["{collection_id}"] = {collection_id.upper()}_WORKFLOW
'''
    print(workflow_template)
    
    # 4. Create directory structure
    archives_dir = Path(__file__).parent / "archives" / collection_id
    archives_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n📁 Created directory: {archives_dir}")
    
    print(f"\n✅ Collection '{name}' created!")
    print(f"\n💡 Next steps:")
    print(f"   1. Copy the code above into supabase_sync.py and workflows.py")
    print(f"   2. Process emails: python archive_cli.py run {collection_id}")
    print(f"   3. Sync to Supabase: python auto_sync_supabase.py")
    
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Create a new collection")
    parser.add_argument('collection_id', help='Collection ID (e.g., mixed_nuts)')
    parser.add_argument('name', help='Display name (e.g., "Mixed Nuts")')
    parser.add_argument('--release-type', default='Track', help='Release type (default: Track)')
    parser.add_argument('--color', default='#8b5cf6', help='Hex color code (default: #8b5cf6)')
    parser.add_argument('--description', default='', help='Collection description')
    
    args = parser.parse_args()
    
    create_collection(
        collection_id=args.collection_id,
        name=args.name,
        release_type=args.release_type,
        color=args.color,
        description=args.description
    )
