interface SummaryViewProps {
  content: string;
}

export const SummaryView = ({ content }: SummaryViewProps) => {
  return (
    <div className="prose prose-sm dark:prose-invert max-w-none">
      <div className="text-sm text-foreground leading-relaxed whitespace-pre-wrap">
        {content}
      </div>
    </div>
  );
};
