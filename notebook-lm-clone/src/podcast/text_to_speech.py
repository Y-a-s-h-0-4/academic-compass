import logging
import os
import asyncio
import io
import tempfile
import soundfile as sf
from typing import List, Dict, Any
from pathlib import Path
from dataclasses import dataclass
import numpy as np

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

from src.podcast.script_generator import PodcastScript

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AudioSegment:
    """Represents a single audio segment with metadata"""
    speaker: str
    text: str
    audio_data: Any
    duration: float
    file_path: str


class PodcastTTSGenerator:
    def __init__(self, lang_code: str = 'eng', sample_rate: int = 16000):
        self.sample_rate = sample_rate
        if not EDGE_TTS_AVAILABLE:
            raise ImportError("edge-tts is required for TTS generation")

        # Single TTS engine (Edge)
        self.speaker_voices = {
            "Speaker 1": "en-US-AriaNeural",  # Female
            "Speaker 2": "en-US-GuyNeural",   # Male
        }
        logger.info("Edge-TTS initialized as the sole TTS engine")
    
    def generate_podcast_audio(
        self, 
        podcast_script: PodcastScript,
        output_dir: str = "outputs/podcast_audio",
        combine_audio: bool = True
    ) -> List[str]:

        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Generating podcast audio for {podcast_script.total_lines} segments")
        logger.info(f"Output directory: {output_dir}")
        
        audio_segments = []
        output_files = []
        
        for i, line_dict in enumerate(podcast_script.script):
            speaker, dialogue = next(iter(line_dict.items()))
            
            logger.info(f"Processing segment {i+1}/{podcast_script.total_lines}: {speaker}")
            
            try:
                segment_audio = self._generate_single_segment(speaker, dialogue)
                segment_filename = f"segment_{i+1:03d}_{speaker.replace(' ', '_').lower()}.wav"
                segment_path = os.path.join(output_dir, segment_filename)
                
                sf.write(segment_path, segment_audio, self.sample_rate)
                output_files.append(segment_path)
                
                if combine_audio:
                    audio_segment = AudioSegment(
                        speaker=speaker,
                        text=dialogue,
                        audio_data=segment_audio,
                        duration=len(segment_audio) / self.sample_rate,
                        file_path=segment_path
                    )
                    audio_segments.append(audio_segment)
                
                logger.info(f"✓ Generated segment {i+1}: {segment_filename}")
                
            except Exception as e:
                logger.error(f"✗ Failed to generate segment {i+1}: {str(e)}")
                continue
        
        if combine_audio and audio_segments:
            combined_path = self._combine_audio_segments(audio_segments, output_dir)
            output_files.append(combined_path)
        
        logger.info(f"Podcast generation complete! Generated {len(output_files)} files")
        return output_files
    
    def _generate_single_segment(self, speaker: str, text: str) -> Any:
        voice = self.speaker_voices.get(speaker, "en-US-AriaNeural")
        clean_text = self._clean_text_for_tts(text)

        async def synthesize():
            # Save to temporary WAV file
            communicate = edge_tts.Communicate(clean_text, voice)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_path = tmp_file.name
            try:
                await communicate.save(tmp_path)
                data, sr = sf.read(tmp_path, dtype="float32")
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

            if sr != self.sample_rate:
                ratio = self.sample_rate / sr
                target_len = int(len(data) * ratio)
                data = np.interp(
                    np.linspace(0, len(data), target_len, endpoint=False),
                    np.arange(len(data)),
                    data,
                )
            return data.astype(np.float32)

        return asyncio.run(synthesize())
    
    def _clean_text_for_tts(self, text: str) -> str:
        import re
        
        clean_text = text.strip()
        
        # Remove citation numbers like [1], [2], [3] etc.
        clean_text = re.sub(r'\[\d+\]', '', clean_text)
        
        # Remove markdown headers (# Header, ## Header, etc.)
        clean_text = re.sub(r'^#{1,6}\s+', '', clean_text, flags=re.MULTILINE)
        
        # Remove bold/italic markers (**, __, *, _)
        # Bold: **text** or __text__
        clean_text = re.sub(r'\*\*(.+?)\*\*', r'\1', clean_text)
        clean_text = re.sub(r'__(.+?)__', r'\1', clean_text)
        # Italic: *text* or _text_ (but not when it's part of a word like don't_use_this)
        clean_text = re.sub(r'\*([^\*]+?)\*', r'\1', clean_text)
        clean_text = re.sub(r'(?<!\w)_([^_]+?)_(?!\w)', r'\1', clean_text)
        
        # Remove code blocks (``` or `)
        clean_text = re.sub(r'```[\s\S]*?```', '', clean_text)  # Multi-line code blocks
        clean_text = re.sub(r'`([^`]+?)`', r'\1', clean_text)  # Inline code
        
        # Remove list markers at the start of lines
        # - Item, * Item, + Item
        clean_text = re.sub(r'^[\-\*\+]\s+', '', clean_text, flags=re.MULTILINE)
        # 1. Item, 2. Item (numbered lists)
        clean_text = re.sub(r'^\d+\.\s+', '', clean_text, flags=re.MULTILINE)
        
        # Remove blockquotes (> text)
        clean_text = re.sub(r'^>\s+', '', clean_text, flags=re.MULTILINE)
        
        # Remove horizontal rules (---, ***, ___)
        clean_text = re.sub(r'^[\-\*_]{3,}$', '', clean_text, flags=re.MULTILINE)
        
        # Remove multiple spaces that might be left after removing markdown
        clean_text = re.sub(r'\s+', ' ', clean_text)
        
        # Clean up repeated punctuation
        clean_text = clean_text.replace("...", ".")
        clean_text = clean_text.replace("!!", "!")
        clean_text = clean_text.replace("??", "?")

        if not clean_text.endswith(('.', '!', '?')):
            clean_text += '.'
        
        return clean_text.strip()
    
    def _combine_audio_segments(
        self, 
        segments: List[AudioSegment], 
        output_dir: str
    ) -> str:
        logger.info(f"Combining {len(segments)} audio segments")
        
        try:
            import numpy as np
            
            pause_duration = 0.2  # seconds
            pause_samples = int(pause_duration * self.sample_rate)
            pause_audio = np.zeros(pause_samples, dtype=np.float32)
            
            combined_audio = []
            for i, segment in enumerate(segments):
                combined_audio.append(segment.audio_data)
                
                if i < len(segments) - 1:
                    combined_audio.append(pause_audio)
            
            final_audio = np.concatenate(combined_audio)
            
            combined_filename = "complete_podcast.wav"
            combined_path = os.path.join(output_dir, combined_filename)
            sf.write(combined_path, final_audio, self.sample_rate)
            
            duration = len(final_audio) / self.sample_rate
            logger.info(f"✓ Combined podcast saved: {combined_path} (Duration: {duration:.1f}s)")
            
            return combined_path
            
        except Exception as e:
            logger.error(f"✗ Failed to combine audio segments: {str(e)}")
            raise
    
    def generate_single_audio(
        self,
        text: str,
        output_dir: str = "outputs/tts",
        voice: str = "en-US-AriaNeural",
        rate: str = "+20%"  # 1.2x speed = +20% rate
    ) -> str:
        """
        Generate a single audio file from text (no splitting into segments)
        Returns the path to the generated audio file
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Generating single audio file for text (length: {len(text)} chars)")
        
        try:
            clean_text = self._clean_text_for_tts(text)
            logger.info(f"Cleaned text (citations removed): {clean_text[:100]}...")
            
            async def synthesize():
                import time
                communicate = edge_tts.Communicate(clean_text, voice, rate=rate)
                # Use timestamp to avoid caching issues
                timestamp = int(time.time() * 1000)
                output_path = os.path.join(output_dir, f"response_{timestamp}.mp3")
                await communicate.save(output_path)
                return output_path
            
            audio_path = asyncio.run(synthesize())
            logger.info(f"✓ Generated audio file: {audio_path}")
            return audio_path
            
        except Exception as e:
            logger.error(f"✗ Failed to generate audio: {str(e)}")
            raise


if __name__ == "__main__":
    import json
    
    try:
        tts_generator = PodcastTTSGenerator(sample_rate=16000)
        
        sample_script_data = {
            "script": [
                {"Speaker 1": "Welcome everyone to our podcast! Today we're exploring the fascinating world of artificial intelligence."},
                {"Speaker 2": "Thanks for having me! AI is indeed one of the most exciting technological developments of our time."},
                {"Speaker 1": "Let's start with machine learning. Can you explain what makes it so revolutionary?"},
                {"Speaker 2": "Absolutely! Machine learning allows computers to learn from data without being explicitly programmed for every single task."},
                {"Speaker 1": "That's incredible! And deep learning takes this even further, doesn't it?"},
                {"Speaker 2": "Exactly! Deep learning uses neural networks with multiple layers, revolutionizing computer vision and natural language processing."}
            ]
        }
        
        from src.podcast.script_generator import PodcastScript
        test_script = PodcastScript(
            script=sample_script_data["script"],
            source_document="AI Overview Test",
            total_lines=len(sample_script_data["script"]),
            estimated_duration="2 minutes"
        )
        
        print("Generating podcast audio...")
        output_files = tts_generator.generate_podcast_audio(
            test_script,
            output_dir="./podcast_output",
            combine_audio=True
        )
        
        print(f"\nGenerated files:")
        for file_path in output_files:
            print(f"  - {file_path}")
        
        print("\nPodcast TTS test completed successfully!")
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("Please install dependencies: pip install transformers torch scipy")
    except Exception as e:
        print(f"Error: {e}")