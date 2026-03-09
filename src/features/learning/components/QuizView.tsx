import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, XCircle, ChevronRight, RotateCcw, Trophy } from "lucide-react";
import { Button } from "@/components/ui/button";

interface QuizOption {
  id: string;
  text: string;
  isCorrect: boolean;
}

interface QuizQuestion {
  question: string;
  options: QuizOption[];
  explanation?: string;
}

interface QuizViewProps {
  questions: QuizQuestion[];
}

export const QuizView = ({ questions }: QuizViewProps) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [answered, setAnswered] = useState(false);
  const [score, setScore] = useState(0);
  const [finished, setFinished] = useState(false);

  if (!questions || questions.length === 0) {
    return (
      <div className="flex items-center justify-center py-8 text-sm text-muted-foreground">
        No quiz questions available.
      </div>
    );
  }

  const question = questions[currentIndex];

  const handleSelect = (option: QuizOption) => {
    if (answered) return;
    setSelectedId(option.id);
    setAnswered(true);
    if (option.isCorrect) setScore((s) => s + 1);
  };

  const handleNext = () => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex((i) => i + 1);
      setSelectedId(null);
      setAnswered(false);
    } else {
      setFinished(true);
    }
  };

  const restart = () => {
    setCurrentIndex(0);
    setSelectedId(null);
    setAnswered(false);
    setScore(0);
    setFinished(false);
  };

  if (finished) {
    const pct = Math.round((score / questions.length) * 100);
    return (
      <div className="flex flex-col items-center gap-5 py-8 text-center">
        <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
          <Trophy className="w-8 h-8 text-primary" />
        </div>
        <div>
          <p className="text-3xl font-bold text-foreground">{score}/{questions.length}</p>
          <p className="text-sm text-muted-foreground mt-1">{pct}% correct</p>
        </div>
        <p className="text-sm text-muted-foreground">
          {pct === 100 ? "Perfect score! 🎉" : pct >= 70 ? "Great job! 👏" : pct >= 40 ? "Good effort, keep going!" : "Review your material and try again."}
        </p>
        <Button size="sm" variant="outline" onClick={restart}>
          <RotateCcw className="w-3.5 h-3.5 mr-2" /> Try Again
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Progress bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>Question {currentIndex + 1} of {questions.length}</span>
          <span className="font-medium text-primary">{score} correct</span>
        </div>
        <div className="h-1.5 bg-muted rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-primary rounded-full"
            initial={{ width: 0 }}
            animate={{ width: `${((currentIndex + (answered ? 1 : 0)) / questions.length) * 100}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>
      </div>

      {/* Question */}
      <motion.p
        key={currentIndex}
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        className="text-sm font-semibold text-foreground leading-relaxed"
      >
        {question.question}
      </motion.p>

      {/* Options */}
      <div className="space-y-2">
        {question.options.map((option, i) => {
          const isSelected = selectedId === option.id;
          const isCorrectOption = option.isCorrect;
          const showCorrectHighlight = answered && isCorrectOption;
          const showWrongHighlight = answered && isSelected && !isCorrectOption;

          let bgClass = "bg-muted/40 border-border/50 hover:bg-muted/70 hover:border-border";
          if (showCorrectHighlight) {
            bgClass = "bg-green-500/15 border-green-500/60";
          } else if (showWrongHighlight) {
            bgClass = "bg-red-500/15 border-red-500/60";
          } else if (isSelected && !answered) {
            bgClass = "bg-primary/10 border-primary/50";
          }

          return (
            <motion.button
              key={option.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              whileTap={!answered ? { scale: 0.98 } : {}}
              onClick={() => handleSelect(option)}
              disabled={answered}
              className={`w-full p-3 rounded-xl text-left text-sm flex items-center gap-3 border transition-all duration-200 ${bgClass} ${
                !answered ? "cursor-pointer" : "cursor-default"
              }`}
            >
              <span
                className={`w-7 h-7 rounded-lg text-xs flex items-center justify-center font-semibold shrink-0 ${
                  showCorrectHighlight
                    ? "bg-green-500 text-white"
                    : showWrongHighlight
                    ? "bg-red-500 text-white"
                    : "bg-background text-foreground border border-border"
                }`}
              >
                {showCorrectHighlight ? (
                  <CheckCircle2 className="w-4 h-4" />
                ) : showWrongHighlight ? (
                  <XCircle className="w-4 h-4" />
                ) : (
                  String.fromCharCode(65 + i)
                )}
              </span>
              <span className="flex-1 leading-relaxed">{option.text}</span>
            </motion.button>
          );
        })}
      </div>

      {/* Explanation + Next */}
      <AnimatePresence>
        {answered && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="space-y-3 overflow-hidden"
          >
            {question.explanation && (
              <div className={`text-xs p-3 rounded-xl border ${
                selectedId && question.options.find(o => o.id === selectedId)?.isCorrect
                  ? "bg-green-500/10 border-green-500/30 text-green-300"
                  : "bg-red-500/10 border-red-500/30 text-red-300"
              }`}>
                <p className="font-semibold mb-1">
                  {selectedId && question.options.find(o => o.id === selectedId)?.isCorrect
                    ? "✓ Correct!"
                    : "✗ Incorrect"}
                </p>
                <p className="leading-relaxed opacity-90">{question.explanation}</p>
              </div>
            )}

            <Button size="sm" className="w-full" onClick={handleNext}>
              {currentIndex < questions.length - 1 ? (
                <>Next Question <ChevronRight className="w-3.5 h-3.5 ml-1" /></>
              ) : (
                "See Results"
              )}
            </Button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
