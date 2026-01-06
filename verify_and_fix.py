#!/usr/bin/env python3
"""
Audio File Verification & Fix Script

Scans archives for missing audio files and offers to reprocess emails
using their UIDs from raw.json
"""

import os
import json
import sys
from pathlib import Path
from typing import List, Dict, Optional


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


def get_email_uids(release_dir: Path) -> Optional[List[str]]:
    """Extract email UID(s) from raw.json"""
    raw_json_path = release_dir / 'raw.json'
    
    if not raw_json_path.exists():
        return None
    
    try:
        with open(raw_json_path, 'r') as f:
            data = json.load(f)
        
        # UID can be a single value or a list
        uid = data.get('uid')
        if uid is None:
            return None
        
        # Normalize to list
        if isinstance(uid, list):
            return [str(u) for u in uid]
        else:
            return [str(uid)]
    except Exception as e:
        print(f"⚠️  Error reading raw.json: {e}")
        return None

def get_email_message_ids(release_dir: Path) -> Optional[List[str]]:
    """Extract email message-id from raw.sjon"""
    raw_json_path = release_dir / 'raw.json'

    if not raw_json_path.exists():
        return None
    
    try:
        with open(raw_json_path, 'r') as f:
            data = json.load(f)

        message_id = data.get('message_id')
        if message_id is None:
            return None
        
        if isinstance(message_id, list):
            return [str(u) for u in message_id]
        else:
            return [str(message_id)]
        

    except Exception as e:
        print(f"⚠️  Error reading raw.json: {e}")
        return None


def check_release_audio(release_dir: Path) -> Dict:
    """
    Check a single release directory for missing audio files.
    """    
    result = {
        'release_name': release_dir.name,
        'release_dir': str(release_dir),
        'metadata_file': str(release_dir / 'metadata.json'),
        'raw_json': str(release_dir / 'raw.json'),
        'has_metadata': False,
        'has_raw_json': False,
        'audio_dir': str(release_dir / 'audio'),
        'has_audio_dir': False,
        'tracks': [],
        'missing_count': 0,
        'missing_duration_count': 0,
        'total_tracks': 0,
        'uids': None,
        'message-id': None,
    }
    
    metadata_path = release_dir / 'metadata.json'
    raw_json_path = release_dir / 'raw.json'
    audio_dir = release_dir / 'audio'
    
    # Check if raw.json exists and get UIDs
    if raw_json_path.exists():
        result['has_raw_json'] = True
        result['uids'] = get_email_uids(release_dir)
        result['message_ids'] = get_email_message_ids(release_dir)
    
    # Check if metadata exists
    if not metadata_path.exists():
        return result
    
    result['has_metadata'] = True
    
    # Check if audio directory exists
    if not audio_dir.exists():
        result['has_audio_dir'] = False
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
            
        # Check if file exists
        audio_path = audio_dir / audio_file
        exists = audio_path.exists()
        
        # Try .m4a variant
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
            'has_duration': 'duration' in track and track['duration'] is not None,
        }
        
        result['tracks'].append(track_info)
        
        if not exists:
            result['missing_count'] += 1
        
        if not track_info['has_duration']:
            result['missing_duration_count'] += 1
    
    return result


def scan_archives_interactive(base_path: str = None, auto_fix: bool = False):
    """Scan archives and prompt to fix issues"""
    
    archives = find_archive_directories(base_path)
    
    if not archives:
        print("❌ No archive directories found!")
        print(f"   Looking in: {base_path or Path(__file__).parent}")
        return
    
    print(f"\n🔍 Found {len(archives)} archive directories\n")
    
    issues_found = []
    
    for archive in archives:
        print(f"📂 Scanning: {archive.name}")
        releases = find_release_folders(archive)
        print(f"   Found {len(releases)} releases")
        
        for release_dir in releases:
            result = check_release_audio(release_dir)
            
            # Print status
            if result['has_metadata']:
                issues = []
                if result['missing_count'] > 0:
                    issues.append(f"{result['missing_count']}/{result['total_tracks']} files missing")
                if result['missing_duration_count'] > 0:
                    issues.append(f"{result['missing_duration_count']}/{result['total_tracks']} durations missing")
                
                if issues:
                    print(f"   ⚠️  {result['release_name']}: {', '.join(issues)}")
                    issues_found.append((archive.name, result))
                else:
                    print(f"   ✅ {result['release_name']}: All files present with durations")
    
    # Summary
    print(f"\n{'='*80}")
    print(f"Found {len(issues_found)} releases with missing files or durations")
    print(f"{'='*80}\n")
    
    if not issues_found:
        print("✅ All audio files are present with durations!")
        return
    
    # Offer to fix issues
    for archive_name, result in issues_found:
        print(f"\n📦 {result['release_name']} ({archive_name})")
        
        # Report missing files
        if result['missing_count'] > 0:
            print(f"   Missing {result['missing_count']} of {result['total_tracks']} files:")
            missing_tracks = [t for t in result['tracks'] if not t['exists']]
            for track in missing_tracks[:3]:  # Show first 3
                print(f"   - Track {track['track_num']}: {track['title']} ({track['audio_file']})")
            if len(missing_tracks) > 3:
                print(f"   ... and {len(missing_tracks) - 3} more")
        
        # Report missing durations
        if result['missing_duration_count'] > 0:
            print(f"   Missing durations for {result['missing_duration_count']} of {result['total_tracks']} tracks:")
            missing_durations = [t for t in result['tracks'] if not t['has_duration']]
            for track in missing_durations[:3]:  # Show first 3
                print(f"   - Track {track['track_num']}: {track['title']}")
            if len(missing_durations) > 3:
                print(f"   ... and {len(missing_durations) - 3} more")
        
        # Check if we have UIDs to reprocess
        if not result['has_raw_json']:
            print("   ❌ No raw.json found - cannot reprocess")
            continue
        
        if not result['uids']:
            print("   ❌ No UIDs found in raw.json - cannot reprocess")
            continue
        
        print(f"   📧 Email UID(s): {', '.join(result['uids'])}")
        
        # Prompt to reprocess
        if auto_fix:
            response = 'y'
        else:
            try:
                response = input("   Reprocess this email? [Y/n]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\n\n👋 Cancelled by user")
                return
        
        if response in ['', 'y', 'yes']:
            print(f"   🔄 Reprocessing {result['release_name']}...")
            reprocess_release(archive_name, result)
        else:
            print("   ⏭️  Skipped")


def reprocess_release(archive_name: str, result: Dict):
    """Reprocess a release using the email processor"""
    
    # Determine which workflow to use based on archive name
    workflow_map = {
        'sonic_twist_archives': 'sonic_twist',
        'off_the_grid_archives': 'off_the_grid',
        'even_more_cake_archives': 'even_more_cake',
    }
    
    workflow_name = workflow_map.get(archive_name)
    
    if not workflow_name:
        print(f"   ❌ Unknown archive type: {archive_name}")
        return
    
    try:
        # Import here to avoid issues if modules aren't available
        from workflows import get_workflow
        from email_processor import EmailProcessor
        from imap_utils import fetch_emails
        
        workflow = get_workflow(workflow_name)
        processor = EmailProcessor(workflow)
        
        # Fetch and reprocess each UID
        for message_id in result['message_ids']:
            print(f"      Fetching message_id {message_id}...")
            
            imap_args = workflow.to_imap_args()
            imap_args['message_id'] = message_id
            
            found = False
            for msg in fetch_emails(imap_args):
                print(f"      Processing email: {msg.subject}")
                processor.process_single_email(msg, force=True)
                found = True
                break
            
            if not found:
                print(f"      ⚠️  Email with UID {uid} not found in mailbox")
        
        print(f"   ✅ Reprocessing complete!")
        
    except ImportError as e:
        print(f"   ❌ Cannot import required modules: {e}")
        print(f"      Make sure workflows.py and email_processor.py are in the same directory")
    except Exception as e:
        print(f"   ❌ Error during reprocessing: {e}")
        import traceback
        traceback.print_exc()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Verify audio files and offer to reprocess missing ones"
    )
    parser.add_argument(
        '--path', 
        help='Base path to search for archives (default: script directory)'
    )
    parser.add_argument(
        '--auto-fix',
        action='store_true',
        help='Automatically reprocess all issues without prompting'
    )
    
    args = parser.parse_args()
    
    print("🔍 Audio File Verification & Fix Tool")
    print("="*80)
    
    scan_archives_interactive(args.path, args.auto_fix)


if __name__ == "__main__":
    main()
