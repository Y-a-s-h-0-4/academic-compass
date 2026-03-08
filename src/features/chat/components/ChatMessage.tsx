import { motion } from "framer-motion";
import { User, Bot, FileText, ExternalLink, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useState } from "react";

interface Source {
  id: string;
  title: string;
  type: "pdf" | "notes" | "slides" | "link";
  page?: number;
}

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  timestamp?: Date;
  isSpeaking?: boolean;
  onDelete?: () => void;
  messageId?: string;
}

export const ChatMessage = ({ role, content, sources, timestamp, isSpeaking = false, onDelete, messageId }: ChatMessageProps) => {
  const isUser = role === "user";
  const [showDeleteButton, setShowDeleteButton] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`flex gap-4 ${isUser ? 'flex-row-reverse' : ''} group`}
      onMouseEnter={() => !isUser && !isSpeaking && setShowDeleteButton(true)}
      onMouseLeave={() => setShowDeleteButton(false)}
    >
      {/* Avatar */}
      <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${
        isUser ? 'bg-secondary' : 'bg-primary/20'
      }`}>
        {isUser ? (
          <User className="w-5 h-5 text-foreground" />
        ) : (
          <Bot className="w-5 h-5 text-primary" />
        )}
      </div>

      {/* Message content */}
      <div className={`flex-1 max-w-[80%] ${isUser ? 'text-right' : ''}`}>
        <div
          className={`inline-block p-4 rounded-2xl ${
            isUser
              ? 'bg-primary text-primary-foreground rounded-br-sm'
              : 'glass-panel-solid rounded-bl-sm'
          }`}
        >
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{content}</p>
        </div>

        {/* Sources */}
        {sources && sources.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className="mt-3 flex flex-wrap gap-2"
          >
            {sources.map((source) => (
              <Badge
                key={source.id}
                variant="secondary"
                className="flex items-center gap-1.5 px-2.5 py-1 cursor-pointer hover:bg-secondary/80 transition-colors"
              >
                <FileText className="w-3 h-3" />
                <span className="text-xs">{source.title}</span>
                {source.page && (
                  <span className="text-muted-foreground text-xs">p.{source.page}</span>
                )}
                <ExternalLink className="w-3 h-3 text-muted-foreground" />
              </Badge>
            ))}
          </motion.div>
        )}

        {/* Timestamp */}
        {timestamp && (
          <p className="mt-2 text-xs text-muted-foreground">
            {timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </p>
        )}

        {/* Delete Button - shown after TTS finishes */}
        {!isUser && !isSpeaking && showDeleteButton && onDelete && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            className="mt-2"
          >
            <Button
              size="sm"
              variant="destructive"
              className="w-full"
              onClick={onDelete}
            >
              <Trash2 className="w-3 h-3 mr-1" />
              Delete
            </Button>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
};
