#!/usr/bin/env python3
"""
Audio File Verification Script

Scans all archive directories and checks that audio files referenced in 
metadata.json actually exist in the audio/ subdirectory.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Tuple


def find_archive_directories(base_path: str = None) -> List[Path]:
    """Find all archive directories (ending in _archives)"""
    if base_path:
        current_dir = Path(base_path)
    else:
        current_dir = Path(__file__).parent
    
    archives = [
        d for d in current_dir.iterdir() 
        if d.is_dir() and d.name.endswith('_archives')
    ]
    return sorted(archives)


def find_release_folders(archive_dir: Path) -> List[Path]:
    """Find all Issue_* or Volume_* folders within an archive"""
    releases = [
        d for d in archive_dir.iterdir()
        if d.is_dir() and (d.name.startswith('Issue_') or d.name.startswith('Volume_'))
    ]
    return sorted(releases)


def check_release_audio(release_dir: Path) -> Dict:
    """
    Check a single release directory for missing audio files.
    
    Returns dict with:
        - release_name: str
        - metadata_file: str (path to metadata.json)
        - has_metadata: bool
        - audio_dir: str
        - has_audio_dir: bool
        - tracks: List[Dict] with track info and file status
        - missing_count: int
        - total_tracks: int
    """
    result = {
        'release_name': release_dir.name,
        'metadata_file': str(release_dir / 'metadata.json'),
        'has_metadata': False,
        'audio_dir': str(release_dir / 'audio'),
        'has_audio_dir': False,
        'tracks': [],
        'missing_count': 0,
        'total_tracks': 0,
    }
    
    metadata_path = release_dir / 'metadata.json'
    audio_dir = release_dir / 'audio'
    
    # Check if metadata exists
    if not metadata_path.exists():
        return result
    
    result['has_metadata'] = True
    
    # Check if audio directory exists
    if not audio_dir.exists():
        result['has_audio_dir'] = False
        # If there's metadata but no audio dir, that's a problem
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
            tracks = metadata.get('tracks', [])
            result['total_tracks'] = len(tracks)
            result['missing_count'] = len(tracks)
        return result
    
    result['has_audio_dir'] = True
    
    # Load metadata and check each track
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    tracks = metadata.get('tracks', [])
    result['total_tracks'] = len(tracks)
    
    for track in tracks:
        audio_file = track.get('audio_file')
        if not audio_file:
            continue
            
        # Check if file exists (try exact name and common variations)
        audio_path = audio_dir / audio_file
        exists = audio_path.exists()
        
        # If not found, try checking for .m4a version (common issue)
        alt_path = None
        if not exists and audio_file.endswith('.mp3'):
            m4a_name = audio_file.replace('.mp3', '.m4a')
            alt_path = audio_dir / m4a_name
            if alt_path.exists():
                exists = True
                audio_file = m4a_name
        
        track_info = {
            'track_num': track.get('track_num'),
            'title': track.get('title', 'Unknown'),
            'audio_file': audio_file,
            'exists': exists,
            'path': str(audio_path if exists else (alt_path if alt_path else audio_path))
        }
        
        result['tracks'].append(track_info)
        
        if not exists:
            result['missing_count'] += 1
    
    return result


def scan_all_archives(base_path: str = None) -> Dict[str, List[Dict]]:
    """Scan all archives and return complete results"""
    all_results = {}
    
    archives = find_archive_directories(base_path)
    
    for archive in archives:
        print(f"\n📂 Scanning: {archive.name}")
        releases = find_release_folders(archive)
        print(f"   Found {len(releases)} releases")
        
        archive_results = []
        
        for release_dir in releases:
            result = check_release_audio(release_dir)
            archive_results.append(result)
            
            # Print progress
            if result['has_metadata']:
                status = "✅" if result['missing_count'] == 0 else "⚠️"
                print(f"   {status} {result['release_name']}: {result['missing_count']}/{result['total_tracks']} missing")
        
        all_results[archive.name] = archive_results
    
    return all_results


def print_summary(results: Dict[str, List[Dict]]):
    """Print a summary of all findings"""
    print("\n" + "="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)
    
    total_releases = 0
    total_tracks = 0
    total_missing = 0
    releases_with_issues = 0
    
    for archive_name, archive_results in results.items():
        archive_missing = sum(r['missing_count'] for r in archive_results)
        archive_tracks = sum(r['total_tracks'] for r in archive_results)
        archive_issues = sum(1 for r in archive_results if r['missing_count'] > 0)
        
        total_releases += len(archive_results)
        total_tracks += archive_tracks
        total_missing += archive_missing
        releases_with_issues += archive_issues
        
        print(f"\n{archive_name}:")
        print(f"  Releases: {len(archive_results)}")
        print(f"  Total Tracks: {archive_tracks}")
        print(f"  Missing Files: {archive_missing}")
        print(f"  Releases with Issues: {archive_issues}")
    
    print(f"\n{'OVERALL TOTALS':^80}")
    print(f"  Total Releases Scanned: {total_releases}")
    print(f"  Total Tracks: {total_tracks}")
    print(f"  Missing Audio Files: {total_missing}")
    print(f"  Releases with Missing Files: {releases_with_issues}")
    
    if total_missing > 0:
        print(f"\n⚠️  {total_missing} audio files are missing!")
    else:
        print(f"\n✅ All audio files are present!")


def print_detailed_report(results: Dict[str, List[Dict]], output_file: str = None):
    """Print or save a detailed report of missing files"""
    lines = []
    lines.append("\n" + "="*80)
    lines.append("DETAILED MISSING FILES REPORT")
    lines.append("="*80)
    
    for archive_name, archive_results in results.items():
        releases_with_missing = [r for r in archive_results if r['missing_count'] > 0]
        
        if not releases_with_missing:
            continue
        
        lines.append(f"\n{archive_name}:")
        lines.append("-" * 80)
        
        for result in releases_with_missing:
            lines.append(f"\n  {result['release_name']} - Missing {result['missing_count']} of {result['total_tracks']} tracks")
            
            missing_tracks = [t for t in result['tracks'] if not t['exists']]
            for track in missing_tracks:
                lines.append(f"    ❌ Track {track['track_num']}: {track['title']}")
                lines.append(f"       Expected: {track['audio_file']}")
                lines.append(f"       Path: {track['path']}")
    
    report = "\n".join(lines)
    print(report)
    
    if output_file:
        with open(output_file, 'w') as f:
            f.write(report)
        print(f"\n📄 Detailed report saved to: {output_file}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Verify audio files exist for all tracks in archives")
    parser.add_argument('--detailed', action='store_true', help='Show detailed report of missing files')
    parser.add_argument('--output', help='Save detailed report to file')
    parser.add_argument('--json', help='Export results as JSON')
    parser.add_argument('--path', help='Base path to search for archives (default: script directory)')
    
    args = parser.parse_args()
    
    print("🔍 Starting audio file verification...")
    results = scan_all_archives(args.path)
    
    print_summary(results)
    
    if args.detailed or args.output:
        print_detailed_report(results, args.output)
    
    if args.json:
        with open(args.json, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Full results exported to: {args.json}")


if __name__ == "__main__":
    main()