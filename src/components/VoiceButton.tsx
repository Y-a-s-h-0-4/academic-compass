import { motion, AnimatePresence } from "framer-motion";
import { Mic, MicOff, Volume2 } from "lucide-react";
import { Button } from "@/components/ui/button";

interface VoiceButtonProps {
  isListening: boolean;
  isSpeaking: boolean;
  onToggle: () => void;
  disabled?: boolean;
}

export const VoiceButton = ({ isListening, isSpeaking, onToggle, disabled }: VoiceButtonProps) => {
  return (
    <div className="relative">
      {/* Pulse rings when active */}
      <AnimatePresence>
        {isListening && (
          <>
            <motion.div
              className="absolute inset-0 rounded-full bg-primary/30"
              initial={{ scale: 1, opacity: 0.6 }}
              animate={{ scale: 2, opacity: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 1.5, repeat: Infinity }}
            />
            <motion.div
              className="absolute inset-0 rounded-full bg-primary/20"
              initial={{ scale: 1, opacity: 0.4 }}
              animate={{ scale: 2.5, opacity: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 1.5, repeat: Infinity, delay: 0.3 }}
            />
          </>
        )}
      </AnimatePresence>

      {/* Main button */}
      <motion.div
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
      >
        <Button
          variant="voice"
          size="icon-xl"
          onClick={onToggle}
          disabled={disabled}
          className={`relative z-10 ${isListening ? 'bg-primary shadow-glow' : isSpeaking ? 'bg-accent' : 'bg-secondary hover:bg-primary'}`}
        >
          <AnimatePresence mode="wait">
            {isListening ? (
              <motion.div
                key="listening"
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0 }}
              >
                <Mic className="h-7 w-7" />
              </motion.div>
            ) : isSpeaking ? (
              <motion.div
                key="speaking"
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0 }}
              >
                <Volume2 className="h-7 w-7" />
              </motion.div>
            ) : (
              <motion.div
                key="idle"
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0 }}
              >
                <MicOff className="h-7 w-7" />
              </motion.div>
            )}
          </AnimatePresence>
        </Button>
      </motion.div>

      {/* Voice waves visualization */}
      <AnimatePresence>
        {(isListening || isSpeaking) && (
          <motion.div
            className="absolute -bottom-8 left-1/2 -translate-x-1/2 flex items-center gap-1"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
          >
            {[...Array(5)].map((_, i) => (
              <motion.div
                key={i}
                className="w-1 bg-primary rounded-full"
                animate={{
                  height: [8, 20, 8],
                }}
                transition={{
                  duration: 0.5,
                  repeat: Infinity,
                  delay: i * 0.1,
                  ease: "easeInOut",
                }}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
