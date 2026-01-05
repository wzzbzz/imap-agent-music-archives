#!/usr/bin/env python3
"""
Email Archiving CLI - Command-line interface for running workflows
"""

import argparse
import sys
from pathlib import Path

from workflows import list_workflows, get_workflow, WORKFLOWS
from email_processor import EmailProcessor, process_workflow


def cmd_list_workflows(args):
    """List all available workflows"""
    print("\n📋 Available Workflows:\n")
    for name, workflow in WORKFLOWS.items():
        print(f"  • {name}")
        print(f"    {workflow.description}")
        print(f"    → {workflow.base_dir}")
        print()


def cmd_run_workflow(args):
    """Run a specific workflow"""
    try:
        process_workflow(args.workflow, force=args.force)
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)


def cmd_show_workflow(args):
    """Show detailed workflow configuration"""
    try:
        workflow = get_workflow(args.workflow)
        print(f"\n📄 Workflow: {workflow.name}")
        print(f"Description: {workflow.description}")
        print(f"\n📂 Storage:")
        print(f"  Base Dir: {workflow.base_dir}")
        print(f"  Folder Pattern: {workflow.folder_pattern}")
        print(f"\n📧 Email Criteria:")
        print(f"  Sender: {workflow.sender or 'Any'}")
        print(f"  Subject: {workflow.subject_filter or 'Any'}")
        print(f"  Folder: {workflow.imap_folder}")
        if workflow.before_date:
            print(f"  Before: {workflow.before_date}")
        if workflow.after_date:
            print(f"  After: {workflow.after_date}")
        print(f"\n🔧 Processing:")
        print(f"  Release Pattern: {workflow.release_number_pattern}")
        print(f"  Normalize Audio: {workflow.normalize_audio}")
        print(f"  Merge Fragments: {workflow.merge_fragments}")
        print(f"\n⚙️  Attachment Processors:")
        for proc in workflow.attachment_processors:
            print(f"  • {proc.name}")
            print(f"    Patterns: {', '.join(proc.file_patterns)}")
            print(f"    Handler: {proc.handler}")
            if proc.options:
                print(f"    Options: {proc.options}")
        print()
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)


def cmd_process_single(args):
    """Process a single email by UID or Message-ID"""
    try:
        workflow = get_workflow(args.workflow)
        processor = EmailProcessor(workflow)
        
        # Fetch specific email
        from imap_utils import fetch_emails
        imap_args = workflow.to_imap_args()
        
        if args.uid:
            imap_args["uid"] = args.uid
        elif args.message_id:
            imap_args["message_id"] = args.message_id
        else:
            print("❌ Must specify either --uid or --message-id")
            sys.exit(1)
        
        found = False
        for msg in fetch_emails(imap_args):
            processor.process_single_email(msg, force=args.force)
            found = True
            break
        
        if not found:
            print("❌ Email not found")
            sys.exit(1)
            
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)


def cmd_check_status(args):
    """Check status of processed emails for a workflow"""
    try:
        workflow = get_workflow(args.workflow)
        base_dir = Path(workflow.base_dir)
        
        if not base_dir.exists():
            print(f"❌ Directory does not exist: {base_dir}")
            sys.exit(1)
        
        # Find all issue/volume folders
        folders = sorted([
            d for d in base_dir.iterdir() 
            if d.is_dir() and (d.name.startswith("Issue_") or d.name.startswith("Volume_"))
        ])
        
        print(f"\n📊 Status for {workflow.name}:")
        print(f"Base: {base_dir}\n")
        print(f"{'Folder':<20} {'raw.json':<12} {'Audio Files':<12} {'Status'}")
        print("-" * 70)
        
        for folder in folders:
            raw_json = folder / "raw.json"
            audio_dir = folder / "audio"
            
            has_json = "✅" if raw_json.exists() else "❌"
            
            if audio_dir.exists():
                audio_files = list(audio_dir.glob("*.mp3")) + list(audio_dir.glob("*.m4a"))
                audio_count = len(audio_files)
            else:
                audio_count = 0
            
            status = "Complete" if raw_json.exists() and audio_count > 0 else "Incomplete"
            
            print(f"{folder.name:<20} {has_json:<12} {audio_count:<12} {status}")
        
        print()
        
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Email Archiving System - Process emails with configurable workflows"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # List workflows
    list_parser = subparsers.add_parser("list", help="List all available workflows")
    list_parser.set_defaults(func=cmd_list_workflows)
    
    # Show workflow details
    show_parser = subparsers.add_parser("show", help="Show workflow configuration")
    show_parser.add_argument("workflow", help="Workflow name")
    show_parser.set_defaults(func=cmd_show_workflow)
    
    # Run workflow
    run_parser = subparsers.add_parser("run", help="Run a workflow")
    run_parser.add_argument("workflow", help="Workflow name")
    run_parser.add_argument("--force", action="store_true", help="Reprocess existing emails")
    run_parser.set_defaults(func=cmd_run_workflow)
    
    # Process single email
    single_parser = subparsers.add_parser("process-one", help="Process a single email")
    single_parser.add_argument("workflow", help="Workflow name")
    single_parser.add_argument("--uid", help="Email UID")
    single_parser.add_argument("--message-id", help="Email Message-ID")
    single_parser.add_argument("--force", action="store_true", help="Reprocess if exists")
    single_parser.set_defaults(func=cmd_process_single)
    
    # Check status
    status_parser = subparsers.add_parser("status", help="Check processing status")
    status_parser.add_argument("workflow", help="Workflow name")
    status_parser.set_defaults(func=cmd_check_status)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == "__main__":
    main()
