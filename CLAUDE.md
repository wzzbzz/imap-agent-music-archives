# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Email Archiving System is a Python-based tool for archiving emails from IMAP servers (particularly Gmail) with a focus on processing attachments (audio files, documents) and storing metadata. The system is driven by declarative workflow configurations that define IMAP search criteria, folder structures, and attachment processors.

Key features:
- **Workflow-driven**: Each archive workflow (e.g., `sonic_twist`, `off_the_grid`) is a `WorkflowConfig` object that defines behavior
- **Pluggable handlers**: Attachment processors (audio normalization, DOCX text extraction) can be added without modifying core code
- **Supabase integration**: Archives are synced to a Supabase database for web UI consumption
- **CLI interface**: `archive_cli.py` provides commands to list, run, and manage workflows
- **Cron automation**: Scripts run hourly from crontab on production server

## Setup and Development

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Configure Credentials
```bash
# Copy template and edit with real credentials
cp config.py.template config.py
# Edit config.py with IMAP credentials (Gmail app password recommended)

# For Supabase and LLM integrations
cp .env.template .env
# Edit .env with SUPABASE_URL, SUPABASE_SERVICE_KEY, and optional API keys
```

### Install ffmpeg
Needed for audio normalization:
- macOS: `brew install ffmpeg`
- Ubuntu/CentOS: `apt-get install ffmpeg` or `yum install ffmpeg`

## Common CLI Commands

```bash
# List all workflows
python archive_cli.py list

# Show workflow configuration and status
python archive_cli.py show sonic_twist

# Run a workflow (fetch and process new emails)
python archive_cli.py run sonic_twist

# Force reprocess all emails in a workflow
python archive_cli.py run sonic_twist --force

# Process a single email by UID
python archive_cli.py process-one sonic_twist --uid 12345

# Process a single email by Message-ID
python archive_cli.py process-one sonic_twist --message-id "CAMyHBL2Xx..."

# Check how many unprocessed emails remain
python archive_cli.py status sonic_twist
```

## Architecture

### Core Components

1. **workflows.py** - Defines `WorkflowConfig` dataclass with IMAP search criteria, release number extraction patterns, folder naming, and attachment processor list. Also contains the `WORKFLOWS` registry with all defined workflows.

2. **email_processor.py** - `EmailProcessor` class orchestrates the workflow:
   - Fetches emails from IMAP using criteria from `WorkflowConfig`
   - Extracts attachments
   - Runs each attachment through its configured processors
   - Saves raw.json metadata in release folders
   - Tracks processed UIDs to avoid reprocessing

3. **attachment_handlers.py** - Contains handler functions for different attachment types:
   - `normalize_audio()` - Uses ffmpeg-normalize to adjust loudness
   - `extract_docx()` - Extracts text from Word documents using python-docx
   - `process_zip()` - Extracts ZIP archives
   - Handlers are registered in the `HANDLERS` dict and referenced by name in WorkflowConfig

4. **imap_utils.py** - IMAP fetching logic using `imap-tools` library. Returns list of emails matching search criteria.

5. **archive_cli.py** - Command-line interface with subcommands for list, show, run, process-one, status.

6. **supabase_sync.py** - Syncs processed archives to Supabase database tables. Reads raw.json files and creates/updates collection and track records. Runs hourly.

7. **generate_manifests.py** - Creates collections.json and other manifest files (legacy, largely replaced by supabase_sync.py).

8. **generate_track_registry.py** - Creates tracks.json registry (legacy, largely replaced by supabase_sync.py).

9. **utils.py** - Utility functions: sanitization, slugification, UID tracking via JSON registries.

### Data Flow

1. **Run Workflow**: `archive_cli.py run sonic_twist`
2. **Fetch Emails**: `EmailProcessor` queries IMAP using sender, subject_filter, date ranges from WorkflowConfig
3. **Extract Metadata**: Release number extracted from subject via regex pattern
4. **Process Attachments**: Each attachment matched against configured processors and handlers run
5. **Save Archives**: Files saved to `archives/sonic_twist/Issue_123/` with raw.json containing metadata
6. **Track State**: UID added to `archives/sonic_twist/downloaded_uids.json` to avoid reprocessing
7. **Sync to Supabase**: `supabase_sync.py` reads raw.json files and updates database

### Workflow Configuration Example

Workflows are defined in `workflows.py`. Key fields in `WorkflowConfig`:
- `name`, `description`, `collection_type` (bound_volume/playlist/named_release)
- `base_dir`, `folder_pattern` - Where files are stored
- `sender`, `subject_filter` - IMAP search criteria
- `release_number_pattern` - Regex to extract issue/volume number from subject
- `attachment_processors` - List of `AttachmentProcessor` objects defining which handlers to run
- `normalize_audio`, `audio_target_lufs`, `audio_bitrate` - Audio processing settings
- `extract_lyrics_from_docx`, `generate_metadata` - Toggle extra features

### Adding a New Workflow

1. Add a new `WorkflowConfig` object to `workflows.py`:
```python
MY_WORKFLOW = WorkflowConfig(
    name="my_workflow",
    description="My custom workflow",
    collection_type="bound_volume",
    base_dir="my_archives",
    folder_pattern="Issue_{number}",
    sender="sender@example.com",
    subject_filter="My Subject",
    release_number_pattern=r'Issue\s*(\d+)',
    attachment_processors=[
        AttachmentProcessor(
            name="audio",
            file_patterns=["*.mp3"],
            handler="normalize_audio",
            options={"target_lufs": -16.0}
        ),
    ],
)
WORKFLOWS["my_workflow"] = MY_WORKFLOW
```

2. Run it: `python archive_cli.py run my_workflow`

### Adding Custom Attachment Handlers

Add handler function to `attachment_handlers.py`:
```python
def my_custom_handler(attachment, target_dir, extracted_text, options, workflow):
    """Process an attachment. Return list of dicts with processed file metadata."""
    # Your logic here
    return [{"original": "filename.ext", "processed": "output.ext"}]

HANDLERS["my_custom_handler"] = my_custom_handler
```

Then reference in WorkflowConfig: `handler="my_custom_handler"`

## Production / Cron Setup

See `CRON_SETUP.md` for detailed instructions. Default schedule:
- `sonic_twist`: Every hour at :05
- `even_more_cake`: Every hour at :20
- `off_the_grid`: Every hour at :35
- `supabase_sync.py` (manifests/registry): Every hour at :50

Logs are written to `logs/<workflow>.log`. Check cron execution:
```bash
tail -f logs/sonic_twist.log
grep -i error logs/*.log
```

## Testing

Limited test infrastructure. `test_refactor.py` exists but is not part of standard testing workflow. Most validation happens through:
- Dry-run the workflow on a few emails
- Check the generated raw.json and file structure
- Verify supabase_sync outputs match expectations

## Key Files to Know

- `workflows.py` - Where workflow configurations live; start here to understand what's being archived
- `email_processor.py` - Core processing loop; understand this to debug email handling
- `attachment_handlers.py` - Where to add new processors for attachments
- `archive_cli.py` - CLI entry point; read this to understand available commands
- `supabase_sync.py` - Database sync logic; check this if metadata isn't appearing in web UI
- `archives/` - Output directory with release folders and raw.json files
- `config.py` - IMAP credentials (not in git)
- `.env` - Supabase and LLM API keys (not in git)

## Important Notes

- **Credentials**: Never commit `config.py` or `.env` with real credentials. `.gitignore` protects them.
- **Duplicate Processing**: `downloaded_uids.json` and `processed.json` track which UIDs have been processed to avoid redundant work.
- **Audio Normalization**: Requires ffmpeg; options controlled by `audio_target_lufs` and `audio_bitrate` in WorkflowConfig.
- **Metadata Generation**: LLM-based metadata is optional; set `generate_metadata: False` to skip.
- **Message-ID Processing**: `process_by_message_id.py` can process a single email by its RFC Message-ID header, useful for reprocessing specific emails.
- **Supabase Collections**: Each workflow typically maps to one collection in Supabase; display metadata (names, colors, descriptions) is in `COLLECTION_DISPLAY` dict in `supabase_sync.py`.
