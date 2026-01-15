"""
TTS Fallback Module
Provides alternative TTS engines when Kokoro is not available
"""

import logging
from pathlib import Path
from typing import Optional
import asyncio

logger = logging.getLogger(__name__)


class TTSFallback:
    """Fallback TTS using edge-tts, gTTS, or pyttsx3"""
    
    def __init__(self, engine: str = "edge-tts"):
        """
        Initialize TTS Fallback
        
        Args:
            engine: TTS engine to use ('edge-tts', 'gtts', 'pyttsx3')
        """
        self.engine = engine
        self.initialized = False
        self._setup_engine()
    
    def _setup_engine(self):
        """Setup the selected TTS engine"""
        try:
            if self.engine == "edge-tts":
                import edge_tts
                self.tts_engine = edge_tts
                self.voice = "en-US-AriaNeural"  # Default voice
                self.initialized = True
                logger.info("Edge-TTS initialized successfully")
                
            elif self.engine == "gtts":
                from gtts import gTTS
                self.gTTS = gTTS
                self.initialized = True
                logger.info("gTTS initialized successfully")
                
            elif self.engine == "pyttsx3":
                import pyttsx3
                self.tts_engine = pyttsx3.init()
                self.initialized = True
                logger.info("pyttsx3 initialized successfully")
                
            else:
                logger.error(f"Unknown TTS engine: {self.engine}")
                
        except Exception as e:
            logger.error(f"Failed to initialize {self.engine}: {str(e)}")
            self.initialized = False
    
    async def generate_speech_async(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None
    ) -> bool:
        """
        Generate speech from text (async version for edge-tts)
        
        Args:
            text: Text to convert to speech
            output_path: Path to save the audio file
            voice: Voice to use (optional)
            
        Returns:
            bool: True if successful
        """
        if not self.initialized:
            logger.error("TTS engine not initialized")
            return False
        
        try:
            if self.engine == "edge-tts":
                voice_to_use = voice or self.voice
                communicate = self.tts_engine.Communicate(text, voice_to_use)
                await communicate.save(output_path)
                logger.info(f"Generated speech with edge-tts: {output_path}")
                return True
                
            else:
                # For non-async engines, call sync version
                return self.generate_speech(text, output_path, voice)
                
        except Exception as e:
            logger.error(f"Error generating speech: {str(e)}")
            return False
    
    def generate_speech(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None
    ) -> bool:
        """
        Generate speech from text (sync version)
        
        Args:
            text: Text to convert to speech
            output_path: Path to save the audio file
            voice: Voice to use (optional)
            
        Returns:
            bool: True if successful
        """
        if not self.initialized:
            logger.error("TTS engine not initialized")
            return False
        
        try:
            if self.engine == "edge-tts":
                # Use async version
                asyncio.run(self.generate_speech_async(text, output_path, voice))
                return True
                
            elif self.engine == "gtts":
                tts = self.gTTS(text=text, lang='en', slow=False)
                tts.save(output_path)
                logger.info(f"Generated speech with gTTS: {output_path}")
                return True
                
            elif self.engine == "pyttsx3":
                self.tts_engine.save_to_file(text, output_path)
                self.tts_engine.runAndWait()
                logger.info(f"Generated speech with pyttsx3: {output_path}")
                return True
                
        except Exception as e:
            logger.error(f"Error generating speech: {str(e)}")
            return False
    
    def list_voices(self):
        """List available voices for the current engine"""
        if not self.initialized:
            return []
        
        try:
            if self.engine == "edge-tts":
                # Return common edge-tts voices
                return [
                    "en-US-AriaNeural",
                    "en-US-GuyNeural",
                    "en-GB-SoniaNeural",
                    "en-GB-RyanNeural",
                    "en-AU-NatashaNeural",
                    "en-AU-WilliamNeural"
                ]
            elif self.engine == "pyttsx3":
                return [voice.name for voice in self.tts_engine.getProperty('voices')]
            else:
                return ["default"]
                
        except Exception as e:
            logger.error(f"Error listing voices: {str(e)}")
            return []


# Convenience function for quick TTS generation
async def text_to_speech(
    text: str,
    output_path: str,
    engine: str = "edge-tts",
    voice: Optional[str] = None
) -> bool:
    """
    Quick text-to-speech generation
    
    Args:
        text: Text to convert
        output_path: Output file path
        engine: TTS engine ('edge-tts', 'gtts', 'pyttsx3')
        voice: Voice name (optional)
        
    Returns:
        bool: Success status
    """
    tts = TTSFallback(engine=engine)
    return await tts.generate_speech_async(text, output_path, voice)
