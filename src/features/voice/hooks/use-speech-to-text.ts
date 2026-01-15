import { useState, useCallback, useRef, useEffect } from 'react';

interface UseSpeechToTextOptions {
  language?: string;
  continuous?: boolean;
  interimResults?: boolean;
  pauseTimeout?: number; // milliseconds before considering speech ended
  onPauseDetected?: () => void; // callback when silence is detected
}

interface UseSpeechToTextReturn {
  isListening: boolean;
  transcript: string;
  interimTranscript: string;
  error: string | null;
  startListening: () => void;
  stopListening: () => void;
  resetTranscript: () => void;
  isBrowserSupported: boolean;
}

export const useSpeechToText = (
  options: UseSpeechToTextOptions = {}
): UseSpeechToTextReturn => {
  const {
    language = 'en-US',
    continuous = true, // Changed to true for continuous mode
    interimResults = true,
    pauseTimeout = 3000, // 3 seconds default
    onPauseDetected,
  } = options;

  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [error, setError] = useState<string | null>(null);

  const recognitionRef = useRef<any>(null);
  const interimRef = useRef('');
  const pauseTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const lastSpeechTimeRef = useRef<number>(0);
  const lastResultIndexRef = useRef<number>(0); // Track last processed result index
  const onPauseDetectedRef = useRef(onPauseDetected); // Store callback in ref

  // Update callback ref whenever it changes
  useEffect(() => {
    onPauseDetectedRef.current = onPauseDetected;
  }, [onPauseDetected]);

  const isBrowserSupported = useCallback(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    return !!SpeechRecognition;
  }, []);

  const startListening = useCallback(() => {
    if (!isBrowserSupported()) {
      setError('Speech Recognition not supported in this browser');
      return;
    }

    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!recognitionRef.current) {
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = continuous;
      recognitionRef.current.interimResults = interimResults;
      recognitionRef.current.lang = language;

      recognitionRef.current.onstart = () => {
        setIsListening(true);
        setError(null);
        interimRef.current = '';
      };

      recognitionRef.current.onresult = (event: any) => {
        lastSpeechTimeRef.current = Date.now();
        
        // Clear any pending pause timeout
        if (pauseTimeoutRef.current) {
          clearTimeout(pauseTimeoutRef.current);
          pauseTimeoutRef.current = null;
        }

        let finalTranscript = '';
        let interimResult = '';

        // Process NEW results only (from event.resultIndex onwards)
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcriptSegment = event.results[i][0].transcript;

          if (event.results[i].isFinal) {
            finalTranscript += transcriptSegment;
          } else {
            interimResult += transcriptSegment;
          }
        }

        // Only update state if we have NEW content
        if (finalTranscript) {
          setTranscript(finalTranscript);
        }

        if (interimResult) {
          setInterimTranscript(interimResult);
        } else {
          setInterimTranscript('');
        }

        // Set timeout to detect pause after speech
        pauseTimeoutRef.current = setTimeout(() => {
          if (onPauseDetectedRef.current) {
            onPauseDetectedRef.current();
          }
        }, pauseTimeout);
      };

      recognitionRef.current.onerror = (event: any) => {
        setError(`Error: ${event.error}`);
      };

      recognitionRef.current.onend = () => {
        setIsListening(false);
      };
    }

    recognitionRef.current.start();
  }, [continuous, interimResults, language, isBrowserSupported]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      setIsListening(false);
    }
  }, []);

  const resetTranscript = useCallback(() => {
    setTranscript('');
    setInterimTranscript('');
    interimRef.current = '';
  }, []);

  return {
    isListening,
    transcript,
    interimTranscript,
    error,
    startListening,
    stopListening,
    resetTranscript,
    isBrowserSupported: isBrowserSupported(),
  };
};
