import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Paperclip, X, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { VoiceButton } from "@/components/VoiceButton";
import { ChatMessage } from "@/components/ChatMessage";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  sources?: Array<{ id: string; title: string; type: "pdf" | "notes" | "slides" | "link"; page?: number }>;
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
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = () => {
    if (inputValue.trim() && !isLoading) {
      onSendMessage(inputValue.trim());
      setInputValue("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleVoiceToggle = () => {
    setIsListening(!isListening);
    // Voice integration would go here
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
      <div className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin">
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
              <ChatMessage
                key={message.id}
                role={message.role}
                content={message.content}
                sources={message.sources}
                timestamp={message.timestamp}
              />
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
              placeholder="Ask anything about your course..."
              rows={1}
              className="flex-1 bg-transparent resize-none outline-none text-foreground placeholder:text-muted-foreground text-sm min-h-[24px] max-h-[120px]"
              style={{ height: 'auto' }}
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
          {isListening && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-4 flex items-center justify-center gap-3 text-sm text-primary"
            >
              <span className="animate-pulse">● Listening...</span>
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => setIsListening(false)}
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
