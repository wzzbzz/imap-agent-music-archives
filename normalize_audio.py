import os
import shutil
import tempfile
from ffmpeg_normalize import FFmpegNormalize, MediaFile


# Codec and format mapping for different output types
OUTPUT_FORMATS = {
    'original': None,  # Keep original format
    'mp3': {
        'codec': 'libmp3lame',
        'format': 'mp3',
        'extension': '.mp3',
        'bitrate': '320k',
    },
    'ogg': {
        'codec': 'libvorbis',
        'format': 'ogg',
        'extension': '.ogg',
        'bitrate': '192k',
    },
    'm4a': {
        'codec': 'aac',
        'format': 'ipod',
        'extension': '.m4a',
        'bitrate': '192k',
    },
    'flac': {
        'codec': 'flac',
        'format': 'flac',
        'extension': '.flac',
        'bitrate': None,  # Lossless
    },
    'opus': {
        'codec': 'libopus',
        'format': 'opus',
        'extension': '.opus',
        'bitrate': '128k',
    },
}


def normalize_audio(input_path, output_format='original', target_lufs=-16.0, bitrate=None):
    """
    Normalizes audio volume using EBU R128.
    
    Args:
        input_path: Path to input audio file
        output_format: One of 'original', 'mp3', 'ogg', 'm4a', 'flac', 'opus'
        target_lufs: Target loudness level (default: -16.0)
        bitrate: Custom bitrate (e.g., '320k'). If None, uses format default.
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not os.path.exists(input_path):
        print(f"❌ Source file missing: {input_path}")
        return False

    # Validate output format
    if output_format not in OUTPUT_FORMATS:
        print(f"❌ Invalid output format: {output_format}")
        print(f"   Valid options: {', '.join(OUTPUT_FORMATS.keys())}")
        return False
    
    # Get input file info
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    input_dir = os.path.dirname(input_path)
    input_ext = os.path.splitext(input_path)[1].lower()
    
    # Determine output settings
    if output_format == 'original':
        # Keep original format
        codec_map = {
            '.m4a': 'aac',
            '.mp3': 'libmp3lame',
            '.ogg': 'libvorbis',
            '.flac': 'flac',
            '.opus': 'libopus',
            '.wav': 'pcm_s16le',
        }
        
        codec = codec_map.get(input_ext, 'libmp3lame')
        format_name = input_ext[1:]  # Remove the dot
        extension = input_ext
        output_bitrate = bitrate or '320k' if codec != 'flac' else None
    else:
        # Use specified format
        format_config = OUTPUT_FORMATS[output_format]
        codec = format_config['codec']
        format_name = format_config['format']
        extension = format_config['extension']
        output_bitrate = bitrate or format_config['bitrate']
    
    final_filename = f"{base_name}{extension}"
    target_path = os.path.join(input_dir, final_filename)
    
    print(f"🔊 Normalizing: {os.path.basename(input_path)} → {final_filename}")
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_output = os.path.join(tmp_dir, f"norm_{final_filename}")

        # Build extra options
        extra_options = []
        if output_bitrate:
            extra_options.extend(['-b:a', output_bitrate])
        
        # Configure normalizer
        norm = FFmpegNormalize(
            normalization_type='ebu',
            target_level=target_lufs,
            audio_codec=codec,
            output_format=format_name,
            extra_output_options=extra_options,
            print_stats=False
        )
        
        try:
            # Create MediaFile and run
            media_file = MediaFile(norm, input_path, temp_output)
            norm.media_files.append(media_file)
            norm.run_normalization()
            
            # Verify output
            if os.path.exists(temp_output) and os.path.getsize(temp_output) > 0:
                # Remove original if we're changing format
                if target_path != input_path and os.path.exists(input_path):
                    os.remove(input_path)
                
                # Move normalized file to final location
                shutil.move(temp_output, target_path)
                print(f"✅ Success: {final_filename}")
                return True
            else:
                print(f"⚠️  Verification failed: Output was empty")
                return False
                
        except Exception as e:
            print(f"❌ Normalization failed: {e}")
            return False


# Backward compatibility - keep the old function signature
def normalize_audio_to_mp3(input_path):
    """Legacy function - normalizes to MP3"""
    return normalize_audio(input_path, output_format='mp3')
