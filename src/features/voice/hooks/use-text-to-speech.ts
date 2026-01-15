import { useState, useCallback, useRef } from 'react';

interface UseTextToSpeechOptions {
  rate?: number;
  pitch?: number;
  volume?: number;
}

interface UseTextToSpeechReturn {
  isSpeaking: boolean;
  isSupported: boolean;
  speak: (text: string) => void;
  stop: () => void;
  pause: () => void;
  resume: () => void;
}

export const useTextToSpeech = (
  options: UseTextToSpeechOptions = {}
): UseTextToSpeechReturn => {
  const { rate = 1, pitch = 1, volume = 1 } = options;

  const [isSpeaking, setIsSpeaking] = useState(false);
  const synthRef = useRef<SpeechSynthesis | null>(null);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  const isSupported = useCallback(() => {
    if (typeof window !== 'undefined') {
      return 'speechSynthesis' in window;
    }
    return false;
  }, []);

  const speak = useCallback(
    (text: string) => {
      if (!isSupported()) {
        console.warn('Speech Synthesis not supported');
        return;
      }

      // Stop any ongoing speech
      stop();

      synthRef.current = window.speechSynthesis;
      utteranceRef.current = new SpeechSynthesisUtterance(text);

      utteranceRef.current.rate = rate;
      utteranceRef.current.pitch = pitch;
      utteranceRef.current.volume = volume;

      utteranceRef.current.onstart = () => {
        setIsSpeaking(true);
      };

      utteranceRef.current.onend = () => {
        setIsSpeaking(false);
      };

      utteranceRef.current.onerror = (event: any) => {
        console.error('Speech synthesis error:', event.error);
        setIsSpeaking(false);
      };

      synthRef.current.speak(utteranceRef.current);
    },
    [isSupported, rate, pitch, volume]
  );

  const stop = useCallback(() => {
    if (synthRef.current) {
      synthRef.current.cancel();
      setIsSpeaking(false);
    }
  }, []);

  const pause = useCallback(() => {
    if (synthRef.current) {
      synthRef.current.pause();
    }
  }, []);

  const resume = useCallback(() => {
    if (synthRef.current) {
      synthRef.current.resume();
    }
  }, []);

  return {
    isSpeaking,
    isSupported: isSupported(),
    speak,
    stop,
    pause,
    resume,
  };
};
