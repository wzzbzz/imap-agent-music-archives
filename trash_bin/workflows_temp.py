    # Metadata Options
    merge_fragments: bool = False  # For multi-part emails
    extract_lyrics_from_docx: bool = True
    generate_metadata: bool = True  # Generate metadata.json using LLM
    metadata_llm_provider: str = "gemini"  # "gemini", "openai", or "anthropic"
    metadata_schema: Optional[Dict] = None  # Custom schema (uses default if None)
    
    # Single Release Mode (for collections like Mixed Nuts)
    single_release_mode: bool = False  # All emails append to one growing release
    single_release_name: str = ""  # Name of the single release folder
    
    # Registry
    registry_filename: str = "downloaded_uids.json"
    processed_filename: str = "processed.json"
