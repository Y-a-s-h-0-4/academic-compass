import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Paperclip, X, Sparkles, Volume2, ArrowDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { VoiceButton } from "./VoiceButton";
import { ChatMessage } from "./ChatMessage";
import { useSpeechToText } from "@/features/voice/hooks/use-speech-to-text";
import { useTextToSpeech } from "@/features/voice/hooks/use-text-to-speech";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  sources?: Array<{ id: string; title: string; type: "pdf" | "notes" | "slides" | "link"; page?: number }>;
  audioPreview?: string;
}

interface ConversationCanvasProps {
  courseName?: string;
  messages: Message[];
  onSendMessage: (content: string) => void;
  isLoading?: boolean;
}

export const ConversationCanvas = ({
  courseName,
  messages,
  onSendMessage,
  isLoading = false,
}: ConversationCanvasProps) => {
  const [inputValue, setInputValue] = useState("");
  const [isVoiceModeActive, setIsVoiceModeActive] = useState(false);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  
  // Track voice input state to prevent duplication
  const voiceInputRef = useRef<string>(""); // Store accumulated final text
  const lastProcessedInterimRef = useRef<string>(""); // Track last interim to avoid duplication

  // Create a stable callback for pause detection
  const handleSendMessage = useCallback(() => {
    if (inputValue.trim() && !isLoading) {
      onSendMessage(inputValue.trim());
      setInputValue("");
      voiceInputRef.current = ""; // Clear voice input on send
      lastProcessedInterimRef.current = ""; // Clear interim tracking
    }
  }, [inputValue, isLoading, onSendMessage]);

  // Speech to text hook with continuous mode and pause detection
  const {
    isListening,
    transcript,
    interimTranscript,
    startListening,
    stopListening,
    resetTranscript,
  } = useSpeechToText({
    language: "en-US",
    continuous: true, // Keep listening continuously
    interimResults: true,
    pauseTimeout: 2000, // 2 seconds pause detection
    onPauseDetected: () => {
      // Auto-send message after 2 second pause
      handleSendMessage();
    },
  });

  // Text to speech hook
  const { isSpeaking, speak, stop: stopSpeaking } = useTextToSpeech({
    rate: 1,
    pitch: 1,
    volume: 1,
  });

  const scrollToBottom = () => {
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
      setIsAtBottom(true);
    }, 0);
  };

  // Detect scroll position
  const handleScroll = useCallback(() => {
    if (!messagesContainerRef.current) return;
    
    const { scrollTop, scrollHeight, clientHeight } = messagesContainerRef.current;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
    
    console.log("Scroll detected:", { scrollTop, scrollHeight, clientHeight, distanceFromBottom });
    
    // Show button if more than 100px from bottom
    setIsAtBottom(distanceFromBottom < 100);
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Auto-speak assistant messages when they arrive
  useEffect(() => {
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      if (lastMessage.role === "assistant" && !isSpeaking) {
        // Automatically speak the assistant response
        speak(lastMessage.content);
      }
    }
  }, [messages, speak, isSpeaking]);

  // Handle final transcript (confirmed speech)
  useEffect(() => {
    if (transcript && isVoiceModeActive) {
      // Add final transcript to our tracking ref
      voiceInputRef.current += transcript + " ";
      
      // Update input value with accumulated voice text + current interim
      setInputValue((prev) => {
        // Remove old interim if exists
        let cleanedText = prev;
        if (lastProcessedInterimRef.current) {
          cleanedText = prev.replace(lastProcessedInterimRef.current, "").trim();
        }
        
        // Combine accumulated voice text with current interim
        const combined = voiceInputRef.current.trim() + (interimTranscript ? " " + interimTranscript : "");
        return combined;
      });
      
      // Reset transcript to prevent re-processing
      resetTranscript();
    }
  }, [transcript, isVoiceModeActive, interimTranscript, resetTranscript]);

  // Handle interim transcript (as user is speaking)
  useEffect(() => {
    if (isListening && isVoiceModeActive && interimTranscript && interimTranscript !== lastProcessedInterimRef.current) {
      lastProcessedInterimRef.current = interimTranscript;
      
      setInputValue((prev) => {
        // Remove previous interim text and add new one
        const baseText = voiceInputRef.current.trim();
        return baseText ? baseText + " " + interimTranscript : interimTranscript;
      });
    }
  }, [interimTranscript, isListening, isVoiceModeActive]);

  const handleSend = handleSendMessage;

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleVoiceToggle = () => {
    if (isListening) {
      // Stop listening and deactivate voice mode
      stopListening();
      setIsVoiceModeActive(false);
      voiceInputRef.current = "";
      lastProcessedInterimRef.current = "";
    } else {
      // Start listening and activate continuous voice mode
      setIsVoiceModeActive(true);
      voiceInputRef.current = "";
      lastProcessedInterimRef.current = "";
      resetTranscript();
      startListening();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-6 py-4 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h2 className="font-serif text-xl text-foreground">
              {courseName || "Learning Assistant"}
            </h2>
            <p className="text-xs text-muted-foreground">
              Voice-first, course-scoped AI copilot
            </p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div 
        ref={messagesContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto overflow-x-hidden p-6 space-y-6 scrollbar-thin relative"
      >
        {messages.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col items-center justify-center h-full text-center"
          >
            <div className="w-20 h-20 rounded-2xl bg-primary/10 flex items-center justify-center mb-6">
              <Sparkles className="w-10 h-10 text-primary" />
            </div>
            <h3 className="font-serif text-2xl text-foreground mb-3">
              Ready to learn together
            </h3>
            <p className="text-muted-foreground max-w-md mb-8">
              Ask me anything about your course materials. I'll only answer from the resources you've uploaded.
            </p>
            <div className="flex flex-wrap gap-3 justify-center max-w-lg">
              {[
                "Explain the key concepts",
                "Quiz me on Chapter 3",
                "Create a mind map",
                "What are my weak areas?",
              ].map((suggestion) => (
                <Button
                  key={suggestion}
                  variant="outline"
                  size="sm"
                  onClick={() => onSendMessage(suggestion)}
                  className="text-sm"
                >
                  {suggestion}
                </Button>
              ))}
            </div>
          </motion.div>
        ) : (
          <>
            {messages.map((message) => (
              <div key={message.id} className="group relative">
                <ChatMessage
                  role={message.role}
                  content={message.content}
                  sources={message.sources}
                  timestamp={message.timestamp}
                  isSpeaking={isSpeaking && message.role === "assistant"}
                  messageId={message.id}
                  onDelete={() => {
                    setMessages((prev) => prev.filter((m) => m.id !== message.id));
                  }}
                />
                {/* Text to speech button for assistant messages */}
                {message.role === "assistant" && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    whileHover={{ opacity: 1 }}
                    className="absolute top-0 right-0 mt-2 mr-2"
                  >
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => {
                        if (isSpeaking) {
                          stopSpeaking();
                        } else {
                          speak(message.content);
                        }
                      }}
                      className="bg-primary/10 hover:bg-primary/20 text-primary"
                    >
                      <Volume2 className="w-4 h-4" />
                    </Button>
                  </motion.div>
                )}
              </div>
            ))}
            {isLoading && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex items-center gap-3"
              >
                <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center">
                  <Sparkles className="w-5 h-5 text-primary animate-pulse" />
                </div>
                <div className="flex gap-1">
                  {[0, 1, 2].map((i) => (
                    <motion.div
                      key={i}
                      className="w-2 h-2 rounded-full bg-primary"
                      animate={{ y: [0, -8, 0] }}
                      transition={{
                        duration: 0.6,
                        repeat: Infinity,
                        delay: i * 0.1,
                      }}
                    />
                  ))}
                </div>
              </motion.div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}

        {/* Scroll to bottom button - positioned absolutely inside container */}
        <AnimatePresence>
          {!isAtBottom && messages.length > 0 && (
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              className="absolute bottom-6 right-6 z-10"
            >
              <Button
                onClick={scrollToBottom}
                size="icon"
                className="rounded-full shadow-lg bg-primary hover:bg-primary/90 w-12 h-12 flex items-center justify-center"
                title="Scroll to latest message"
              >
                <ArrowDown className="w-5 h-5" />
              </Button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-border">
        <div className="flex items-end gap-4">
          {/* Voice Button */}
          <VoiceButton
            isListening={isListening}
            isSpeaking={isSpeaking}
            onToggle={handleVoiceToggle}
          />

          {/* Text Input */}
          <div className="flex-1 glass-panel-solid p-3 flex items-end gap-3">
            <Button variant="ghost" size="icon-sm" className="flex-shrink-0">
              <Paperclip className="w-4 h-4" />
            </Button>
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything about your course... or use the mic button"
              rows={1}
              className="flex-1 bg-transparent resize-none outline-none text-foreground placeholder:text-muted-foreground text-sm min-h-[24px] max-h-[120px]"
            />
            <Button
              variant="glow"
              size="icon-sm"
              onClick={handleSend}
              disabled={!inputValue.trim() || isLoading}
              className="flex-shrink-0"
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Voice Status */}
        <AnimatePresence>
          {isListening && isVoiceModeActive && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-4 flex items-center justify-between gap-3 text-sm text-primary px-3"
            >
              <div className="flex items-center gap-2">
                <span className="animate-pulse">● Listening...</span>
                {interimTranscript && (
                  <span className="text-muted-foreground">"{interimTranscript}"</span>
                )}
              </div>
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => {
                  stopListening();
                  setIsVoiceModeActive(false);
                }}
                className="hover:bg-destructive/20 text-destructive"
              >
                <X className="w-4 h-4" />
              </Button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};
