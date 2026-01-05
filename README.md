# Email Archiving System

A modular, configuration-driven system for archiving emails with attachments from IMAP servers.

## Features

- ✅ **Declarative Configuration** - Workflows defined as data, not code
- ✅ **Pluggable Handlers** - Easy to add new attachment processors
- ✅ **Separation of Concerns** - Clear module boundaries
- ✅ **Reusable Components** - Same code handles all workflows
- ✅ **CLI Interface** - Easy workflow management
- ✅ **Type Hints** - Better IDE support and documentation

## Installation

### Prerequisites

- Python 3.7+
- ffmpeg (for audio normalization)

### Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd email_archiving
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure credentials**
   ```bash
   cp config.py.template config.py
   # Edit config.py with your IMAP credentials
   ```

4. **Install ffmpeg** (if using audio normalization)
   - macOS: `brew install ffmpeg`
   - Ubuntu: `apt-get install ffmpeg`
   - Windows: Download from [ffmpeg.org](https://ffmpeg.org)

## Quick Start

### List Available Workflows

```bash
python archive_cli.py list
```

### Show Workflow Configuration

```bash
python archive_cli.py show sonic_twist
```

### Run a Workflow

```bash
# Process all new emails
python archive_cli.py run sonic_twist

# Reprocess everything (force)
python archive_cli.py run sonic_twist --force
```

### Check Processing Status

```bash
python archive_cli.py status sonic_twist
```

### Process Single Email

```bash
# By UID
python archive_cli.py process-one sonic_twist --uid 12345

# By Message-ID
python archive_cli.py process-one sonic_twist --message-id "CAMyHBL2Xx..."
```

## Architecture

### Core Components

1. **workflows.py** - Declarative workflow configurations
2. **email_processor.py** - Core email processing logic
3. **attachment_handlers.py** - Pluggable attachment processors
4. **imap_utils.py** - IMAP email fetching
5. **utils.py** - Utility functions
6. **archive_cli.py** - Command-line interface

## Creating a New Workflow

Edit `workflows.py` and add a new `WorkflowConfig`:

```python
MY_WORKFLOW = WorkflowConfig(
    name="my_workflow",
    description="My custom workflow",
    base_dir="my_archives",
    folder_pattern="Episode_{number}",
    
    # IMAP criteria
    sender="sender@example.com",
    subject_filter="Newsletter",
    
    # Release number extraction
    release_number_pattern=r'Episode\s*(\d+)',
    
    # Attachment processing
    attachment_processors=[
        AttachmentProcessor(
            name="audio_normalizer",
            file_patterns=["*.mp3"],
            handler="normalize_audio"
        ),
    ],
)

# Add to registry
WORKFLOWS["my_workflow"] = MY_WORKFLOW
```

## Creating Custom Handlers

Add to `attachment_handlers.py`:

```python
def my_custom_handler(attachment, target_dir, extracted_text, options, workflow):
    """
    Custom attachment processor.
    
    Returns: List[Dict] with metadata about processed files
    """
    # Your processing logic here
    return [{"original": filename, "slugified": slugged_name}]

# Register it
HANDLERS["my_custom_handler"] = my_custom_handler
```

## Workflow Configuration Options

### WorkflowConfig Fields

- **name** - Workflow identifier
- **description** - Human-readable description
- **base_dir** - Root directory for archives
- **folder_pattern** - Template for folder names (e.g., "Issue_{number}")
- **imap_folder** - IMAP folder to search (default: "[Gmail]/All Mail")
- **sender** - Filter by sender email
- **subject_filter** - Filter by subject text
- **before_date** - Filter emails before date (format: MM/DD/YY)
- **after_date** - Filter emails after date
- **require_attachments** - Only process emails with attachments
- **exclude_patterns** - Tuple of patterns to exclude (e.g., ("re:", "fwd:"))
- **release_number_pattern** - Regex to extract release number
- **release_number_fallback** - Fallback regex if primary fails
- **attachment_processors** - List of AttachmentProcessor configs
- **normalize_audio** - Enable audio normalization
- **audio_target_lufs** - Target loudness level
- **audio_bitrate** - Target audio bitrate
- **merge_fragments** - Merge multi-part emails
- **extract_lyrics_from_docx** - Extract text from .docx files

### AttachmentProcessor Fields

- **name** - Processor identifier
- **file_patterns** - List of glob patterns (e.g., ["*.mp3", "*.wav"])
- **handler** - Handler function name from attachment_handlers.py
- **options** - Dict of handler-specific options

## Built-in Workflows

### sonic_twist
- Newsletters with audio tracks and lyrics
- Processes ZIP files, normalizes audio, extracts lyrics from DOCX

### off_the_grid
- Radio show archives with audio
- Processes ZIP files, normalizes audio

### even_more_cake
- Radio show archives with multi-part emails
- Processes ZIP files, normalizes audio, merges fragments

## Dependencies

- imap-tools - IMAP email fetching
- python-docx - Extract text from Word documents
- ffmpeg-normalize - Audio normalization
- dataclasses (Python 3.7+)
- pathlib (Python 3.4+)

## Security Notes

⚠️ **Important**: Never commit `config.py` with real credentials to version control! The `.gitignore` file is configured to exclude it.

For Gmail users, use an [App Password](https://support.google.com/accounts/answer/185833) instead of your main password.

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
