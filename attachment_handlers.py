"""
Attachment Handlers - Pluggable processors for different attachment types
"""

import os
import zipfile
import io
from pathlib import Path
from typing import Dict, List, Optional
from docx import Document

from utils import clean_text, slugify_filename
from normalize_audio import normalize_audio


def process_zip_attachment(attachment, target_dir: Path, extracted_text: Dict, 
                          options: Dict, workflow) -> List[Dict]:
    """
    Unzip attachment and process contents.
    
    Options:
        - extract_to: subdirectory to extract to (default: current)
    """
    extract_dir = target_dir / options.get("extract_to", "")
    extract_dir.mkdir(parents=True, exist_ok=True)
    
    saved_files = []
    
    print(f"📦 Unzipping: {attachment.filename}")
    
    with zipfile.ZipFile(io.BytesIO(attachment.payload)) as z:
        for file_info in z.infolist():
            # Filter out system junk
            filename = os.path.basename(file_info.filename)
            if not filename or filename.startswith('.') or filename.startswith('__'):
                continue
            
            # Slugify for safety
            slugged_name = slugify_filename(filename)
            file_path = extract_dir / slugged_name
            
            # Extract file
            with z.open(file_info.filename) as source, open(file_path, 'wb') as target:
                target.write(source.read())
            
            # Track original extracted file info
            file_metadata = {
                "original": filename,
                "slugified": slugged_name,
                "path": str(file_path.relative_to(target_dir.parent))
            }
            
            # Process extracted file with other handlers
            # Check if it matches any patterns from workflow
            was_processed = False
            for processor_config in workflow.attachment_processors:
                if processor_config.name == "zip_extractor":
                    continue  # Skip self
                    
                handler = get_handler(processor_config.handler)
                if _matches_pattern(slugged_name, processor_config.file_patterns):
                    # Create a mock attachment object for the extracted file
                    class ExtractedFile:
                        def __init__(self, path):
                            self.filename = path.name
                            with open(path, 'rb') as f:
                                self.payload = f.read()
                    
                    extracted_att = ExtractedFile(file_path)
                    handler_result = handler(
                        attachment=extracted_att,
                        target_dir=extract_dir,
                        extracted_text=extracted_text,
                        options=processor_config.options,
                        workflow=workflow
                    )
                    
                    # Update metadata with processed filename (e.g., .m4a -> .mp3)
                    if handler_result and len(handler_result) > 0:
                        file_metadata["slugified"] = handler_result[0].get("slugified", slugged_name)
                        file_metadata["path"] = str((extract_dir / file_metadata["slugified"]).relative_to(target_dir.parent))
                    
                    was_processed = True
                    break  # Only process with first matching handler
            
            saved_files.append(file_metadata)
    
    print(f"✅ Extracted {len(saved_files)} files from ZIP")
    return saved_files


def normalize_audio_handler(attachment, target_dir: Path, extracted_text: Dict,
                           options: Dict, workflow) -> List[Dict]:
    """
    Save audio file and normalize it.
    
    Options:
        - target_lufs: target loudness (default: workflow setting or -16.0)
        - bitrate: target bitrate (default: workflow setting or "320k")
        - output_format: output format (default: workflow setting or "original")
    """
    orig_name = clean_text(attachment.filename)
    slugged_name = slugify_filename(orig_name)
    file_path = target_dir / slugged_name
    
    # Save file
    with open(file_path, 'wb') as f:
        f.write(attachment.payload)
    
    print(f"🎵 Processing audio: {orig_name}")
    
    # Normalize if enabled in workflow
    if workflow.normalize_audio:
        output_format = options.get('output_format', workflow.audio_output_format)
        target_lufs = options.get('target_lufs', workflow.audio_target_lufs)
        bitrate = options.get('bitrate', workflow.audio_bitrate)
        
        normalize_audio(
            str(file_path),
            output_format=output_format,
            target_lufs=target_lufs,
            bitrate=bitrate
        )
        
        # Determine final filename after normalization
        base_name = os.path.splitext(slugged_name)[0]
        original_ext = os.path.splitext(slugged_name)[1].lower()
        
        if output_format == 'original':
            # Kept original format, filename unchanged
            final_name = slugged_name
        else:
            # Format was converted - update extension
            from normalize_audio import OUTPUT_FORMATS
            if output_format in OUTPUT_FORMATS and OUTPUT_FORMATS[output_format]:
                new_ext = OUTPUT_FORMATS[output_format]['extension']
                final_name = f"{base_name}{new_ext}"
            else:
                final_name = slugged_name
        
        slugged_name = final_name
    
    return [{
        "original": orig_name,
        "slugified": slugged_name,
        "type": "audio"
    }]


def extract_docx_text(attachment, target_dir: Path, extracted_text: Dict,
                     options: Dict, workflow) -> List[Dict]:
    """
    Save docx file and extract text content.
    
    Options:
        - field_name: name of field to store extracted text (default: "extracted_text")
    """
    orig_name = clean_text(attachment.filename)
    slugged_name = slugify_filename(orig_name)
    file_path = target_dir / slugged_name
    
    # Save file
    with open(file_path, 'wb') as f:
        f.write(attachment.payload)
    
    # Extract text
    if workflow.extract_lyrics_from_docx:
        try:
            doc = Document(file_path)
            text = "\n".join([para.text for para in doc.paragraphs])
            field_name = options.get("field_name", "extracted_text")
            extracted_text[field_name] = text
            print(f"📝 Extracted text from {orig_name}")
        except Exception as e:
            print(f"⚠️  Could not extract text from {orig_name}: {e}")
    
    return [{
        "original": orig_name,
        "slugified": slugged_name,
        "type": "document"
    }]


def save_image(attachment, target_dir: Path, extracted_text: Dict,
              options: Dict, workflow) -> List[Dict]:
    """Save image file without processing"""
    orig_name = clean_text(attachment.filename)
    slugged_name = slugify_filename(orig_name)
    file_path = target_dir / slugged_name
    
    with open(file_path, 'wb') as f:
        f.write(attachment.payload)
    
    return [{
        "original": orig_name,
        "slugified": slugged_name,
        "type": "image"
    }]


# Handler Registry
HANDLERS = {
    "process_zip_attachment": process_zip_attachment,
    "normalize_audio": normalize_audio_handler,
    "extract_docx_text": extract_docx_text,
    "save_image": save_image,
}


def get_handler(handler_name: str):
    """Get a handler function by name"""
    if handler_name not in HANDLERS:
        raise ValueError(f"Unknown handler: {handler_name}. Available: {list(HANDLERS.keys())}")
    return HANDLERS[handler_name]


def register_handler(name: str, handler_func):
    """Register a custom handler"""
    HANDLERS[name] = handler_func


def _matches_pattern(filename: str, patterns: List[str]) -> bool:
    """Check if filename matches any pattern"""
    import fnmatch
    filename_lower = filename.lower()
    return any(fnmatch.fnmatch(filename_lower, pattern.lower()) for pattern in patterns)
