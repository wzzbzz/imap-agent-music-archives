#!/usr/bin/env python3
"""
Process a single email by Message-ID for any collection.
This allows manual curation of specific emails.
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from workflows import get_workflow
from email_processor import EmailProcessor
from imap_utils import fetch_emails


def get_next_track_number(base_dir: Path, pattern_prefix: str = "Track_") -> int:
    """Find the next available track number."""
    if not base_dir.exists():
        return 1
    
    existing = [
        int(d.name.replace(pattern_prefix, ""))
        for d in base_dir.iterdir()
        if d.is_dir() and d.name.startswith(pattern_prefix) and d.name.replace(pattern_prefix, "").isdigit()
    ]
    
    return max(existing, default=0) + 1


def process_by_message_id(message_id: str, workflow_name: str, track_number: int = None):
    """
    Process a specific email by its Message-ID.
    
    Args:
        message_id: The Message-ID header from the email
        workflow_name: Workflow to use (e.g., mixed_nuts, sonic_twist)
        track_number: Optional track number (auto-assigned if None)
    """
    workflow = get_workflow(workflow_name)
    processor = EmailProcessor(workflow)
    
    print(f"🔍 Looking for email with Message-ID: {message_id}")
    
    # Auto-assign track number if not provided
    if track_number is None and workflow_name == "mixed_nuts":
        base_dir = Path(workflow.base_dir)
        track_number = get_next_track_number(base_dir)
        print(f"🔢 Auto-assigned Track number: {track_number}")
    
    # Fetch emails but filter by message-id
    imap_args = workflow.to_imap_args()
    imap_args['message_id'] = message_id
    
    found = False
    for msg in fetch_emails(imap_args):
        found = True
        print(f"\n✅ Found email: {msg.subject}")
        
        try:
            # Temporarily inject track number into subject if needed
            if track_number and workflow_name == "mixed_nuts":
                # Modify the subject to include track number
                original_subject = msg.subject
                msg.subject = f"Track {track_number} - {original_subject}"
                print(f"📝 Using subject: {msg.subject}")
            
            processor.process_single_email(msg, force=True)
            processor._mark_processed(msg.uid)
            print(f"\n✅ Successfully processed!")
            
        except Exception as e:
            print(f"\n❌ Error processing: {e}")
            return False
    
    if not found:
        print(f"\n❌ No email found with Message-ID: {message_id}")
        print(f"\n💡 Make sure:")
        print(f"   - The Message-ID is exact (including <>)")
        print(f"   - The email is in your Gmail account")
        return False
    
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Process a specific email by Message-ID"
    )
    parser.add_argument(
        'workflow',
        help='Workflow to use (e.g., mixed_nuts, sonic_twist)'
    )
    parser.add_argument(
        'message_id',
        help='Message-ID from email header (e.g., "<CAMyHBL2...@mail.gmail.com>")'
    )
    parser.add_argument(
        '--track-number',
        type=int,
        help='Track number (auto-assigned for mixed_nuts if not provided)'
    )
    
    args = parser.parse_args()

    if not args.message_id or not args.message_id.strip():
        print("❌ Error: message_id cannot be empty")
        sys.exit(1)
    
    success = process_by_message_id(args.message_id, args.workflow, args.track_number)
    sys.exit(0 if success else 1)
