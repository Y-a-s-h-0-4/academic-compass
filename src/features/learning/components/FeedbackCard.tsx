import { motion } from "framer-motion";

export interface QuestionFeedbackPayload {
  what_you_got_right: string[];
  what_was_incorrect: Array<{ student_claim: string; correction: string }>;
  what_you_missed: string[];
  question_tip: string;
}

interface FeedbackCardProps {
  feedback: QuestionFeedbackPayload;
}

const BulletList = ({ items }: { items: string[] }) => {
  if (!items.length) {
    return <p className="text-xs text-muted-foreground">No items detected for this section.</p>;
  }

  return (
    <ul className="list-disc pl-4 space-y-1 text-sm text-foreground/90">
      {items.map((item, index) => (
        <li key={`${item}-${index}`}>{item}</li>
      ))}
    </ul>
  );
};

export const FeedbackCard = ({ feedback }: FeedbackCardProps) => {
  const right = Array.isArray(feedback.what_you_got_right) ? feedback.what_you_got_right : [];
  const missed = Array.isArray(feedback.what_you_missed) ? feedback.what_you_missed : [];
  const incorrect = Array.isArray(feedback.what_was_incorrect) ? feedback.what_was_incorrect : [];
  const tip = (feedback.question_tip || "Review the concept and solve one similar question.").trim();

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-border/70 bg-card/80 p-4 space-y-3"
    >
      <div>
        <p className="text-sm font-semibold text-green-700">What you got right</p>
        <BulletList items={right} />
      </div>

      <div>
        <p className="text-sm font-semibold text-red-700">What was incorrect</p>
        {incorrect.length === 0 ? (
          <p className="text-xs text-muted-foreground">No incorrect claims identified.</p>
        ) : (
          <ul className="space-y-2 text-sm">
            {incorrect.map((item, index) => (
              <li key={`${item.student_claim}-${index}`} className="rounded-md border border-red-200/70 bg-red-50/40 p-2">
                <p className="text-foreground"><span className="font-medium">Claim:</span> {item.student_claim}</p>
                <p className="text-foreground"><span className="font-medium">Correction:</span> {item.correction}</p>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <p className="text-sm font-semibold text-amber-700">What you missed</p>
        <BulletList items={missed} />
      </div>

      <div className="rounded-md border border-primary/20 bg-primary/5 p-3">
        <p className="text-sm font-semibold text-primary">Tip</p>
        <p className="text-sm text-foreground/90">{tip}</p>
      </div>
    </motion.div>
  );
};
