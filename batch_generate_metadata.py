#!/usr/bin/env python3
"""
Batch Metadata Generator

Scans archives and generates metadata.json files for releases that only have raw.json
"""

import sys
from pathlib import Path
from typing import List

def find_releases_needing_metadata(base_dir: Path) -> List[Path]:
    """Find release folders that have raw.json but no metadata.json"""
    releases_needing_metadata = []
    
    # Find all archive directories
    archives = [d for d in base_dir.iterdir() if d.is_dir() and d.name.endswith('_archives')]
    
    for archive in archives:
        # Find all Issue_* or Volume_* folders
        releases = [
            d for d in archive.iterdir()
            if d.is_dir() and (d.name.startswith('Issue_') or d.name.startswith('Volume_'))
        ]
        
        for release_dir in releases:
            raw_json = release_dir / 'raw.json'
            metadata_json = release_dir / 'metadata.json'
            
            if raw_json.exists() and not metadata_json.exists():
                releases_needing_metadata.append(release_dir)
    
    return sorted(releases_needing_metadata)


def batch_generate_metadata(base_path: str = None, provider: str = "gemini", 
                           force: bool = False, limit: int = None):
    """
    Generate metadata for all releases that need it.
    
    Args:
        base_path: Base directory to search (default: script directory)
        provider: LLM provider ("gemini", "openai", "anthropic")
        force: Regenerate even if metadata.json exists
        limit: Maximum number of releases to process
    """
    from llm_metadata import generate_metadata_for_release
    import time
    
    if base_path:
        base_dir = Path(base_path)
    else:
        base_dir = Path(__file__).parent
    
    print(f"🔍 Scanning for releases in: {base_dir}")
    print(f"   LLM Provider: {provider.upper()}")
    print(f"   Force regenerate: {force}")
    
    # Find releases
    if force:
        # Find all releases (ignoring metadata.json existence)
        archives = [d for d in base_dir.iterdir() if d.is_dir() and d.name.endswith('_archives')]
        releases_to_process = []
        for archive in archives:
            releases = [
                d for d in archive.iterdir()
                if d.is_dir() and (d.name.startswith('Issue_') or d.name.startswith('Volume_'))
                and (d / 'raw.json').exists()
            ]
            releases_to_process.extend(releases)
        releases_to_process.sort()
    else:
        releases_to_process = find_releases_needing_metadata(base_dir)
    
    if not releases_to_process:
        print("\n✅ All releases already have metadata!")
        return
    
    print(f"\n📊 Found {len(releases_to_process)} releases needing metadata")
    
    if limit:
        releases_to_process = releases_to_process[:limit]
        print(f"   Processing first {limit} releases")
    
    # Process each release
    success_count = 0
    fail_count = 0
    
    for i, release_dir in enumerate(releases_to_process, 1):
        print(f"\n[{i}/{len(releases_to_process)}] Processing {release_dir.name}...")
        
        try:
            success = generate_metadata_for_release(
                release_dir=release_dir,
                provider=provider
            )
            
            if success:
                success_count += 1
            else:
                fail_count += 1
            
            # Rate limit throttling (5 seconds between calls)
            if i < len(releases_to_process):
                print("⏳ Throttling: Waiting 5 seconds...")
                time.sleep(5)
                
        except KeyboardInterrupt:
            print("\n\n👋 Cancelled by user")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            fail_count += 1
            continue
    
    # Summary
    print(f"\n{'='*80}")
    print(f"BATCH PROCESSING COMPLETE")
    print(f"{'='*80}")
    print(f"  ✅ Successful: {success_count}")
    print(f"  ❌ Failed: {fail_count}")
    print(f"  📊 Total: {success_count + fail_count}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Batch generate metadata.json files for email archives"
    )
    parser.add_argument(
        '--path',
        help='Base path to search for archives (default: script directory)'
    )
    parser.add_argument(
        '--provider',
        default='gemini',
        choices=['gemini', 'openai', 'anthropic'],
        help='LLM provider to use (default: gemini)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Regenerate metadata even if it already exists'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Maximum number of releases to process'
    )
    
    args = parser.parse_args()
    
    batch_generate_metadata(
        base_path=args.path,
        provider=args.provider,
        force=args.force,
        limit=args.limit
    )


if __name__ == "__main__":
    main()
