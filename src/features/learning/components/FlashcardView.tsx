import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronLeft, ChevronRight, RotateCcw, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Flashcard {
  front: string;
  back: string;
}

interface FlashcardViewProps {
  cards: Flashcard[];
}

export const FlashcardView = ({ cards }: FlashcardViewProps) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [direction, setDirection] = useState(0); // -1 left, 1 right

  if (!cards || cards.length === 0) {
    return (
      <div className="flex items-center justify-center py-8 text-sm text-muted-foreground">
        No flashcards available.
      </div>
    );
  }

  const card = cards[currentIndex];

  const goTo = (newIndex: number) => {
    setDirection(newIndex > currentIndex ? 1 : -1);
    setIsFlipped(false);
    setCurrentIndex(newIndex);
  };

  const next = () => {
    if (currentIndex < cards.length - 1) goTo(currentIndex + 1);
  };

  const prev = () => {
    if (currentIndex > 0) goTo(currentIndex - 1);
  };

  const restart = () => {
    setDirection(-1);
    setIsFlipped(false);
    setCurrentIndex(0);
  };

  const slideVariants = {
    enter: (dir: number) => ({ x: dir > 0 ? 200 : -200, opacity: 0 }),
    center: { x: 0, opacity: 1 },
    exit: (dir: number) => ({ x: dir > 0 ? -200 : 200, opacity: 0 }),
  };

  return (
    <div className="flex flex-col items-center gap-4">
      {/* Counter dots */}
      <div className="flex items-center gap-1.5">
        {cards.map((_, i) => (
          <button
            key={i}
            onClick={() => goTo(i)}
            className={`h-1.5 rounded-full transition-all duration-200 ${
              i === currentIndex
                ? "w-6 bg-primary"
                : "w-1.5 bg-muted-foreground/30 hover:bg-muted-foreground/50"
            }`}
          />
        ))}
      </div>

      <p className="text-xs text-muted-foreground font-medium">
        {currentIndex + 1} / {cards.length}
      </p>

      {/* Card carousel */}
      <div className="w-full relative overflow-hidden" style={{ minHeight: 220 }}>
        <AnimatePresence mode="wait" custom={direction}>
          <motion.div
            key={currentIndex}
            custom={direction}
            variants={slideVariants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="w-full"
          >
            <div className="w-full rounded-2xl border border-border bg-gradient-to-br from-card to-muted/30 shadow-sm overflow-hidden">
              {/* Front - Question */}
              <div className="p-5 border-b border-border/50">
                <p className="text-[10px] uppercase tracking-widest text-primary font-semibold mb-2">
                  Question
                </p>
                <p className="text-sm font-medium text-foreground leading-relaxed">
                  {card.front}
                </p>
              </div>

              {/* Back - Answer (hidden until flipped) */}
              <AnimatePresence>
                {isFlipped && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.25 }}
                    className="overflow-hidden"
                  >
                    <div className="p-5 bg-primary/5">
                      <p className="text-[10px] uppercase tracking-widest text-green-400 font-semibold mb-2">
                        Answer
                      </p>
                      <p className="text-sm text-foreground leading-relaxed">
                        {card.back}
                      </p>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Flip button */}
      <Button
        variant={isFlipped ? "secondary" : "default"}
        size="sm"
        onClick={() => setIsFlipped(!isFlipped)}
        className="gap-2"
      >
        <RefreshCw className={`w-3.5 h-3.5 transition-transform ${isFlipped ? "rotate-180" : ""}`} />
        {isFlipped ? "Hide Answer" : "Flip to Reveal"}
      </Button>

      {/* Navigation */}
      <div className="flex items-center gap-3">
        <Button variant="outline" size="icon-sm" onClick={prev} disabled={currentIndex === 0}>
          <ChevronLeft className="w-4 h-4" />
        </Button>
        <Button variant="outline" size="icon-sm" onClick={restart} title="Restart">
          <RotateCcw className="w-3 h-3" />
        </Button>
        <Button variant="outline" size="icon-sm" onClick={next} disabled={currentIndex === cards.length - 1}>
          <ChevronRight className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
};
