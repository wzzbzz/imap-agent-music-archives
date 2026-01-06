"""
LLM Metadata Generator - Creates structured metadata from raw email data

Supports multiple LLM providers:
- Gemini (Google)
- OpenAI (GPT-4)
- Anthropic (Claude)
"""

import os
import json
import time
from typing import Dict, Optional, List
from pathlib import Path

# Optional imports - only import if available
try:
    import google.generativeai as genai
    import google.api_core.exceptions
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class MetadataGenerator:
    """Generate structured metadata from raw email data using LLMs"""
    
    def __init__(self, provider: str = "gemini", api_key: Optional[str] = None):
        """
        Initialize the metadata generator.
        
        Args:
            provider: "gemini", "openai", or "anthropic"
            api_key: API key for the provider (if None, reads from config)
        """
        self.provider = provider.lower()
        
        # Get API key
        if api_key is None:
            from config import GEMINI_KEY, OPENAI_KEY
            if self.provider == "gemini":
                api_key = GEMINI_KEY
            elif self.provider == "openai":
                api_key = OPENAI_KEY
        
        self.api_key = api_key
        
        # Initialize provider
        if self.provider == "gemini":
            if not GEMINI_AVAILABLE:
                raise ImportError("google-generativeai not installed. Run: pip install google-generativeai")
            genai.configure(api_key=self.api_key)
            # Try multiple model names in case one doesn't work
            model_names = [
                'models/gemini-2.5-flash',      # Latest fast model
                'models/gemini-flash-latest',    # Fallback
                'models/gemini-2.0-flash',       # Older fast version
                'models/gemini-pro-latest',      # Pro version
            ]
            self.model = None
            for model_name in model_names:
                try:
                    self.model = genai.GenerativeModel(model_name)
                    print(f"✓ Using Gemini model: {model_name}")
                    break
                except Exception as e:
                    continue
            
            if self.model is None:
                raise ValueError("Could not initialize any Gemini model. Check API key and available models.")
        
        elif self.provider == "openai":
            if not OPENAI_AVAILABLE:
                raise ImportError("openai not installed. Run: pip install openai")
            self.client = openai.OpenAI(api_key=self.api_key)
        
        elif self.provider == "anthropic":
            if not ANTHROPIC_AVAILABLE:
                raise ImportError("anthropic not installed. Run: pip install anthropic")
            self.client = anthropic.Anthropic(api_key=self.api_key)
        
        else:
            raise ValueError(f"Unknown provider: {provider}. Use 'gemini', 'openai', or 'anthropic'")
    
    def generate_metadata(self, raw_data: Dict, schema: Dict, max_retries: int = 5) -> Dict:
        """
        Generate structured metadata from raw email data.
        
        Args:
            raw_data: Dict with 'subject', 'body', 'attachments'
            schema: Expected JSON schema structure
            max_retries: Max retry attempts for rate limits
        
        Returns:
            Dict with structured metadata
        """
        prompt = self._build_prompt(raw_data, schema)
        
        for attempt in range(max_retries):
            try:
                if self.provider == "gemini":
                    return self._call_gemini(prompt)
                elif self.provider == "openai":
                    return self._call_openai(prompt)
                elif self.provider == "anthropic":
                    return self._call_anthropic(prompt)
                    
            except Exception as e:
                # Handle rate limits
                if "429" in str(e) or "ResourceExhausted" in str(type(e).__name__):
                    wait_time = (attempt + 1) * 12  # 12s, 24s, 36s...
                    print(f"⏳ Rate limit hit. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise e
        
        raise Exception(f"Max retries ({max_retries}) exceeded")
    
    def _build_prompt(self, raw_data: Dict, schema: Dict) -> str:
        """Build the LLM prompt from raw data and schema"""
        
        # Format attachments for display
        attachments_list = raw_data.get('attachments', [])
        if isinstance(attachments_list, list) and len(attachments_list) > 0:
            if isinstance(attachments_list[0], dict):
                attachments_str = json.dumps(attachments_list, indent=2)
            else:
                attachments_str = str(attachments_list)
        else:
            attachments_str = "[]"
        
        prompt = f"""Extract structured metadata from this music release newsletter.

Respond with valid JSON only. Follow the schema exactly.

IMPORTANT NOTES:
- Numbers in filenames do NOT indicate track order - use the order from the message body
- Use the "slugified" filename from attachments (the processed version)
- Escape all special characters properly in JSON
- the FIRST image is the release image.
- all subsequent images should be assumed to be the track images in order.

SUBJECT: {raw_data.get('subject', 'Unknown')}

ATTACHMENTS AVAILABLE:
{attachments_str}

MESSAGE BODY:
{raw_data.get('body', '')}

EXPECTED SCHEMA:
{json.dumps(schema, indent=2)}

Return ONLY valid JSON matching the schema above."""
        
        return prompt
    
    def _call_gemini(self, prompt: str) -> Dict:
        """Call Gemini API"""
        response = self.model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)
    
    def _call_openai(self, prompt: str) -> Dict:
        """Call OpenAI API"""
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a metadata extraction assistant. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    
    def _call_anthropic(self, prompt: str) -> Dict:
        """Call Anthropic API"""
        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        # Extract JSON from response
        text = response.content[0].text
        # Try to parse as JSON
        return json.loads(text)


def generate_metadata_for_release(release_dir: Path, provider: str = "gemini", 
                                   schema: Optional[Dict] = None) -> bool:
    """
    Generate metadata.json for a release from its raw.json
    
    Args:
        release_dir: Path to release directory (e.g., Issue_1)
        provider: LLM provider to use
        schema: Expected schema (uses default if None)
    
    Returns:
        bool: True if successful
    """
    raw_json_path = release_dir / "raw.json"
    metadata_json_path = release_dir / "metadata.json"
    
    if not raw_json_path.exists():
        print(f"❌ No raw.json found in {release_dir.name}")
        return False
    
    # Load raw data
    with open(raw_json_path, 'r') as f:
        raw_data = json.load(f)
    
    # Use default schema if none provided
    if schema is None:
        schema = {
            "release_number": "int",
            "release_image": "string (filename)",
            "tracks": [
                {
                    "track_num": "int",
                    "title": "string",
                    "credits": "string",
                    "date_written": "string (YYYY-MM-DD)",
                    "lyrics": "string",
                    "audio_file": "string (slugified filename)",
                    "track_image": "string (filename)"
                }
            ]
        }
    
    print(f"🧠 Generating metadata for {release_dir.name}...")
    
    try:
        generator = MetadataGenerator(provider=provider)
        metadata = generator.generate_metadata(raw_data, schema)
        
        # Save metadata
        with open(metadata_json_path, 'w') as f:
            json.dump(metadata, f, indent=4)
        
        print(f"✅ Metadata saved to {metadata_json_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error generating metadata: {e}")
        return False


def list_available_gemini_models():
    """List all available Gemini models for your API key"""
    if not GEMINI_AVAILABLE:
        print("❌ google-generativeai not installed")
        return
    
    try:
        from config import GEMINI_KEY
        genai.configure(api_key=GEMINI_KEY)
        
        print("📋 Available Gemini Models:")
        for model in genai.list_models():
            if 'generateContent' in model.supported_generation_methods:
                print(f"  • {model.name}")
    except Exception as e:
        print(f"❌ Error listing models: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--list-models":
        list_available_gemini_models()
    else:
        # Example usage
        from pathlib import Path
        
        release_dir = Path("sonic_twist_archives/Issue_1")
        generate_metadata_for_release(release_dir, provider="gemini")
