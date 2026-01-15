import { motion, AnimatePresence } from "framer-motion";
import { X, Brain, HelpCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { FeedbackCard } from "@/features/learning/components/FeedbackCard";

interface Resource {
  id: string;
  title: string;
  type: "pdf" | "notes" | "slides" | "audio" | "link";
  uploadedAt: Date;
  size?: string;
  status: "processing" | "ready" | "error";
}

interface Feedback {
  type: "strength" | "weakness" | "missed";
  topic: string;
  description: string;
  trend?: "up" | "down" | "stable";
  confidence?: number;
}

interface RightPanelProps {
  isOpen: boolean;
  onClose: () => void;
  feedback: Feedback[];
  onStartQuiz: () => void;
}

export const RightPanel = ({
  isOpen,
  onClose,
  feedback,
  onStartQuiz,
}: RightPanelProps) => {

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ x: 100, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 100, opacity: 0 }}
          transition={{ type: "spring", damping: 25, stiffness: 300 }}
          className="w-80 h-full bg-card border-l border-border flex flex-col"
        >
          {/* Header */}
          <div className="p-4 border-b border-border flex items-center justify-between">
            <h3 className="font-serif text-lg text-foreground">Learning Insights</h3>
            <Button variant="ghost" size="icon-sm" onClick={onClose}>
              <X className="w-4 h-4" />
            </Button>
          </div>

          {/* Feedback Content */}
          <div className="flex-1 overflow-hidden flex flex-col">
              <div className="p-4 flex-1 overflow-y-auto scrollbar-thin space-y-4">
                {feedback.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-center py-8">
                    <div className="w-16 h-16 rounded-2xl bg-secondary flex items-center justify-center mb-4">
                      <Brain className="w-8 h-8 text-muted-foreground" />
                    </div>
                    <h4 className="font-medium text-foreground mb-2">No feedback yet</h4>
                    <p className="text-sm text-muted-foreground mb-4">
                      Take a quiz to start tracking your progress
                    </p>
                    <Button onClick={onStartQuiz} size="sm">
                      <HelpCircle className="w-4 h-4 mr-2" />
                      Start Quiz
                    </Button>
                  </div>
                ) : (
                  feedback.map((item, index) => (
                    <FeedbackCard key={index} {...item} />
                  ))
                )}
              </div>

              {feedback.length > 0 && (
                <div className="p-4 border-t border-border">
                  <Button onClick={onStartQuiz} className="w-full">
                    <HelpCircle className="w-4 h-4 mr-2" />
                    Take Quiz
                  </Button>
                </div>
              )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
