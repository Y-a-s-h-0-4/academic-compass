import { motion } from "framer-motion";
import { useState } from "react";
import { CheckCircle2, XCircle, HelpCircle, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

interface QuizOption {
  id: string;
  text: string;
  isCorrect: boolean;
}

interface QuizCardProps {
  question: string;
  options: QuizOption[];
  explanation?: string;
  onAnswer: (optionId: string, isCorrect: boolean) => void;
  onNext?: () => void;
}

export const QuizCard = ({
  question,
  options,
  explanation,
  onAnswer,
  onNext,
}: QuizCardProps) => {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showResult, setShowResult] = useState(false);

  const handleSelect = (option: QuizOption) => {
    if (showResult) return;
    
    setSelectedId(option.id);
    setShowResult(true);
    onAnswer(option.id, option.isCorrect);
  };

  const selectedOption = options.find(o => o.id === selectedId);
  const isCorrect = selectedOption?.isCorrect;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="glass-panel-solid p-6 max-w-2xl mx-auto"
    >
      {/* Question */}
      <div className="flex items-start gap-3 mb-6">
        <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
          <HelpCircle className="w-5 h-5 text-primary" />
        </div>
        <h3 className="font-serif text-xl text-foreground leading-relaxed">{question}</h3>
      </div>

      {/* Options */}
      <div className="space-y-3 mb-6">
        {options.map((option, index) => {
          const isSelected = selectedId === option.id;
          const showCorrect = showResult && option.isCorrect;
          const showWrong = showResult && isSelected && !option.isCorrect;

          return (
            <motion.button
              key={option.id}
              whileHover={!showResult ? { scale: 1.01, x: 4 } : {}}
              whileTap={!showResult ? { scale: 0.99 } : {}}
              onClick={() => handleSelect(option)}
              disabled={showResult}
              className={`w-full p-4 rounded-xl text-left transition-all flex items-center gap-4 ${
                showCorrect
                  ? 'bg-success/10 border-2 border-success text-foreground'
                  : showWrong
                  ? 'bg-destructive/10 border-2 border-destructive text-foreground'
                  : isSelected
                  ? 'bg-primary/10 border-2 border-primary text-foreground'
                  : 'bg-secondary hover:bg-secondary/80 border-2 border-transparent'
              }`}
            >
              <span className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm font-medium ${
                showCorrect
                  ? 'bg-success text-success-foreground'
                  : showWrong
                  ? 'bg-destructive text-destructive-foreground'
                  : 'bg-muted text-muted-foreground'
              }`}>
                {String.fromCharCode(65 + index)}
              </span>
              <span className="flex-1 text-sm">{option.text}</span>
              {showCorrect && <CheckCircle2 className="w-5 h-5 text-success" />}
              {showWrong && <XCircle className="w-5 h-5 text-destructive" />}
            </motion.button>
          );
        })}
      </div>

      {/* Result & Explanation */}
      {showResult && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-4"
        >
          <div className={`p-4 rounded-xl ${
            isCorrect ? 'bg-success/10 border border-success/20' : 'bg-destructive/10 border border-destructive/20'
          }`}>
            <div className="flex items-center gap-2 mb-2">
              {isCorrect ? (
                <>
                  <CheckCircle2 className="w-5 h-5 text-success" />
                  <span className="font-medium text-success">Correct!</span>
                </>
              ) : (
                <>
                  <XCircle className="w-5 h-5 text-destructive" />
                  <span className="font-medium text-destructive">Not quite right</span>
                </>
              )}
            </div>
            {explanation && (
              <p className="text-sm text-muted-foreground">{explanation}</p>
            )}
          </div>

          {onNext && (
            <Button onClick={onNext} className="w-full" size="lg">
              Next Question
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          )}
        </motion.div>
      )}
    </motion.div>
  );
};
