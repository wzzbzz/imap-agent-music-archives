"""
Email Processor - Core email processing logic using workflow configurations
"""

import sys
import os
import json
from typing import Dict, List, Optional
from pathlib import Path

# Ensure imports work regardless of how module is executed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from workflows import WorkflowConfig
from imap_utils import fetch_emails
from utils import clean_text, sanitize_for_json, slugify_filename, is_already_downloaded, mark_as_downloaded
from attachment_handlers import get_handler


class EmailProcessor:
    """Processes emails according to a workflow configuration"""
    
    def __init__(self, workflow: WorkflowConfig):
        self.workflow = workflow
        self.base_dir = Path(workflow.base_dir)
        self.base_dir.mkdir(exist_ok=True)
        self.registry_path = self.base_dir / workflow.registry_filename
    
    def _get_latest_archived_date(self) -> Optional[str]:
        """Find the most recent email date from existing raw.json files"""
        from datetime import datetime
        
        if not self.base_dir.exists():
            return None
        
        latest_date = None
        latest_datetime = None
        
        # Scan all subdirectories for raw.json files
        for raw_json_path in self.base_dir.rglob("raw.json"):
            try:
                with open(raw_json_path, 'r') as f:
                    data = json.load(f)
                    date_str = data.get('date')
                    
                    if date_str:
                        # Handle both single date and list of dates
                        if isinstance(date_str, list):
                            date_str = date_str[0] if date_str else None
                        
                        if date_str:
                            # Parse the date string
                            email_date = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
                            
                            if latest_datetime is None or email_date > latest_datetime:
                                latest_datetime = email_date
                                # Format as YYYY/MM/DD for Gmail search (4-digit year required)
                                latest_date = email_date.strftime("%Y/%m/%d")
            
            except Exception as e:
                print(f"⚠️  Could not read date from {raw_json_path}: {e}")
                continue
        
        return latest_date
        
    def process_all_emails(self, force: bool = False, title: Optional[str] = None,
                           message_id: Optional[str] = None):
        """Fetch and process all emails matching workflow criteria"""
        print(f"🚀 Starting workflow: {self.workflow.name}")
        print(f"📂 Base directory: {self.base_dir}")

        # Auto-detect resume point if no after_date is set
        if not self.workflow.after_date:
            latest_date = self._get_latest_archived_date()
            if latest_date:
                print(f"📅 Found latest archived email from {latest_date}")
                print(f"🔍 Fetching only emails newer than this date...")
                self.workflow.after_date = latest_date
            else:
                print(f"📭 No existing archives found - fetching all emails")
        else:
            print(f"📅 Using configured after_date: {self.workflow.after_date}")

        imap_args = self.workflow.to_imap_args()

        # Override message_id if passed at runtime (e.g. nice_threads, mixed_nuts)
        if message_id:
            imap_args["message_id"] = message_id

        for msg in fetch_emails(imap_args):
            if not force and self._is_already_processed(msg.uid):
                print(f"⏭️  UID {msg.uid} already processed. Skipping.")
                continue

            try:
                self.process_single_email(msg, force=force, title=title)
                self._mark_processed(msg.uid)
            except Exception as e:
                print(f"❌ Error processing UID {msg.uid}: {e}")
    
    def process_single_email(self, msg, force: bool = False, title: Optional[str] = None):
        """Process a single email message"""
        print(f"\n📥 Processing UID {msg.uid}: {msg.subject}")

        clean_subject = clean_text(msg.subject)
        collection_type = self.workflow.collection_type

        # Resolve the release folder based on collection type
        if collection_type == "bound_volume":
            release_number = self.workflow.extract_release_number(clean_subject)
            if not str(release_number).isdigit():
                print(f"❌ Could not extract valid release number from: {clean_subject}")
                return
            folder_name = self.workflow.get_folder_name(release_number)
            release_label = f"{self.workflow.release_indicator} {release_number}"

        elif collection_type == "playlist":
            folder_name = self.workflow.single_release_name
            release_label = folder_name

        elif collection_type == "named_release":
            if not title:
                print(f"❌ Workflow '{self.workflow.name}' requires --title")
                return
            from utils import slugify_filename
            folder_name = slugify_filename(title)
            release_label = title

        else:
            print(f"❌ Unknown collection_type: {collection_type}")
            return

        # Setup directories
        issue_dir = self.base_dir / folder_name
        audio_dir = issue_dir / "audio"
        images_dir = issue_dir / "images"

        # Check if already exists
        if not force and issue_dir.exists():
            raw_json = issue_dir / "raw.json"
            if raw_json.exists() and not self.workflow.merge_fragments:
                print(f"⏭️  {release_label} already exists. Skipping.")
                return

        # If force reprocessing, clean out and recreate audio directory
        print(len(msg.attachments))

        if force and audio_dir.exists() and len(msg.attachments) > 0:
            print(f"🗑️  Removing existing audio directory for clean reprocessing...")
            import shutil
            shutil.rmtree(audio_dir)

        # Create necessary directories
        audio_dir.mkdir(parents=True, exist_ok=True)
        images_dir.mkdir(parents=True, exist_ok=True)

        print(f"📄 Processing {release_label}...")
        
        # Process attachments
        attachment_metadata = []
        extracted_text = {}  # For lyrics, notes, etc.
        
        for att in msg.attachments:
            result = self._process_attachment(att, issue_dir, extracted_text)
            if result:
                attachment_metadata.extend(result)
        
        # Build metadata
        self._save_metadata(
            issue_dir=issue_dir,
            msg=msg,
            clean_subject=clean_subject,
            attachment_metadata=attachment_metadata,
            extracted_text=extracted_text
        )
        
        # Generate structured metadata using LLM if enabled
        if self.workflow.generate_metadata:
            self._generate_llm_metadata(issue_dir)

        print(f"✅ {release_label} complete!")
    
    def _process_attachment(self, att, issue_dir: Path, extracted_text: Dict) -> List[Dict]:
        """Process a single attachment according to workflow config"""
        orig_name = clean_text(att.filename)
        
        # Determine target directory based on file type
        if self._is_image(orig_name):
            target_dir = issue_dir / "images"
        else:
            target_dir = issue_dir / "audio"
        
        
        # Find matching processor
        for processor_config in self.workflow.attachment_processors:
            if self._matches_pattern(orig_name, processor_config.file_patterns):
                handler = get_handler(processor_config.handler)
                return handler(
                    attachment=att,
                    target_dir=target_dir,
                    extracted_text=extracted_text,
                    options=processor_config.options,
                    workflow=self.workflow
                )
        
        # No processor matched - save as-is to appropriate directory
        return self._save_raw_attachment(att, target_dir)
    
    def _is_image(self, filename: str) -> bool:
        """Check if filename is an image"""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']
        return any(filename.lower().endswith(ext) for ext in image_extensions)
    
    def _save_raw_attachment(self, att, target_dir: Path) -> List[Dict]:
        """Save attachment without processing"""
        orig_name = clean_text(att.filename)
        slugged_name = slugify_filename(orig_name)
        file_path = target_dir / slugged_name
        
        with open(file_path, 'wb') as f:
            f.write(att.payload)
        
        return [{"original": orig_name, "slugified": slugged_name}]
    
    def _matches_pattern(self, filename: str, patterns: List[str]) -> bool:
        """Check if filename matches any of the given patterns"""
        import fnmatch
        filename_lower = filename.lower()
        return any(fnmatch.fnmatch(filename_lower, pattern.lower()) for pattern in patterns)
    
    def _save_metadata(self, issue_dir: Path, msg, clean_subject: str, 
                      attachment_metadata: List[Dict], extracted_text: Dict):
        """Save or merge email metadata to raw.json"""
        raw_json_path = issue_dir / "raw.json"
        
        # Build new metadata
        new_data = {
            "uid": msg.uid,
            "message_id": msg.obj.get('Message-ID'),
            "subject": clean_subject,
            "body": sanitize_for_json(msg.text or msg.html),
            "date": str(msg.date),
            "from": msg.from_,
            "to": msg.to,
            "attachments": attachment_metadata,
            **extracted_text  # Add any extracted lyrics, notes, etc.
        }
        
        # Merge or create
        if self.workflow.merge_fragments and raw_json_path.exists():
            print("🔗 Merging with existing raw.json...")
            final_data = self._merge_metadata(raw_json_path, new_data)
        else:
            print("🆕 Creating new raw.json...")
            # Initialize list fields for consistency
            new_data["uid"] = [new_data["uid"]]
            new_data["message_id"] = [new_data["message_id"]]
            new_data["subject"] = [new_data["subject"]]
            final_data = new_data
        
        with open(raw_json_path, "w") as f:
            json.dump(final_data, f, indent=4)
    
    def _merge_metadata(self, raw_json_path: Path, new_data: Dict) -> Dict:
        """Merge new metadata with existing"""
        with open(raw_json_path, "r") as f:
            existing = json.load(f)
        
        # Convert single values to lists
        for list_key in ["uid", "message_id", "subject"]:
            if not isinstance(existing.get(list_key), list):
                existing[list_key] = [existing[list_key]] if existing.get(list_key) else []
            
            # Append new value if not duplicate
            new_val = new_data.get(list_key)
            if new_val not in existing[list_key]:
                existing[list_key].append(new_val)
        
        # Merge body text
        existing_body = existing.get("body", "")
        new_body = new_data.get("body", "")
        if new_body and new_body not in existing_body:
            existing["body"] = f"{existing_body}\n\n--- PART 2 ---\n\n{new_body}".strip()
        
        # Merge attachments
        current_attachments = existing.get("attachments", [])
        if isinstance(current_attachments, str):
            current_attachments = json.loads(current_attachments)
        current_attachments.extend(new_data.get("attachments", []))
        existing["attachments"] = current_attachments
        
        return existing
    
    def _generate_llm_metadata(self, issue_dir: Path):
        """Generate structured metadata.json using LLM"""
        try:
            from llm_metadata import generate_metadata_for_release
            
            print(f"🧠 Generating structured metadata with {self.workflow.metadata_llm_provider.upper()}...")
            
            success = generate_metadata_for_release(
                release_dir=issue_dir,
                provider=self.workflow.metadata_llm_provider,
                schema=self.workflow.metadata_schema
            )
            
            if success:
                print(f"✅ Metadata generation complete")
                # Add track durations after LLM generation
                self._add_track_durations(issue_dir)
            else:
                print(f"⚠️  Metadata generation failed (raw.json still available)")
                
        except ImportError as e:
            print(f"⚠️  Could not import LLM metadata generator: {e}")
        except Exception as e:
            print(f"⚠️  Error generating metadata: {e}")
            print(f"   Raw data is still available in raw.json")
    
    def _add_track_durations(self, issue_dir: Path):
        """Add duration field to tracks in metadata.json by reading actual audio files"""
        try:
            from mutagen.mp3 import MP3
            
            metadata_path = issue_dir / "metadata.json"
            if not metadata_path.exists():
                return
            
            print(f"🎵 Adding track durations...")
            
            with open(metadata_path, 'r') as f:
                data = json.load(f)
            
            updated = False
            for track in data.get('tracks', []):
                audio_filename = track.get('audio_file')
                if not audio_filename:
                    continue
                
                # Try audio directory first, then root
                audio_path = issue_dir / "audio" / audio_filename
                if not audio_path.exists():
                    audio_path = issue_dir / audio_filename
                
                if audio_path.exists():
                    try:
                        audio = MP3(str(audio_path))
                        duration = int(audio.info.length)
                        track['duration'] = duration
                        print(f"  ✓ {track.get('title', audio_filename)}: {duration}s")
                        updated = True
                    except Exception as e:
                        print(f"  ⚠️  Could not read duration for {audio_filename}: {e}")
                else:
                    print(f"  ⚠️  Audio file not found: {audio_filename}")
            
            if updated:
                with open(metadata_path, 'w') as f:
                    json.dump(data, f, indent=4)
                print(f"✅ Track durations added")
            
        except ImportError:
            print(f"⚠️  mutagen not installed - skipping duration calculation")
            print(f"   Install with: pip install mutagen")
        except Exception as e:
            print(f"⚠️  Error adding durations: {e}")
    
    def _is_already_processed(self, uid) -> bool:
        """Check if email UID has been processed"""
        return is_already_downloaded(uid, str(self.registry_path))
    
    def _mark_processed(self, uid):
        """Mark email UID as processed"""
        mark_as_downloaded(uid, str(self.registry_path))


def process_workflow(workflow_name: str, force: bool = False,
                     title: Optional[str] = None, message_id: Optional[str] = None):
    """Convenience function to process a workflow by name"""
    from workflows import get_workflow

    workflow = get_workflow(workflow_name)
    processor = EmailProcessor(workflow)
    processor.process_all_emails(force=force, title=title, message_id=message_id)


if __name__ == "__main__":
    # Example usage
    process_workflow("sonic_twist", force=False)
