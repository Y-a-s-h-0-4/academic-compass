import { AlertTriangle, CheckCircle, TrendingUp, TrendingDown, Minus, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import type { SessionFeedbackReport, SessionFeedbackImprovementItem } from "@/lib/notebookApi";

interface SessionReportProps {
  report: SessionFeedbackReport | null;
  isLoading: boolean;
  error: string | null;
  isSaved: boolean;
  onRetry: () => void;
  onSave: () => void;
  onAction: (item: SessionFeedbackImprovementItem) => void;
}

const TrendBadge = ({ trend }: { trend?: string | null }) => {
  const value = (trend || "stable").toLowerCase();
  if (value === "improved") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-green-300 bg-green-100/70 px-2 py-0.5 text-xs text-green-800">
        <TrendingUp className="w-3 h-3" /> Up
      </span>
    );
  }
  if (value === "declined") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-red-300 bg-red-100/70 px-2 py-0.5 text-xs text-red-800">
        <TrendingDown className="w-3 h-3" /> Down
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-slate-300 bg-slate-100/70 px-2 py-0.5 text-xs text-slate-700">
      <Minus className="w-3 h-3" /> Stable
    </span>
  );
};

export const SessionReport = ({
  report,
  isLoading,
  error,
  isSaved,
  onRetry,
  onSave,
  onAction,
}: SessionReportProps) => {
  const showDevFooter = String(import.meta.env.VITE_SHOW_DEV_FOOTERS || "").toLowerCase() === "true";

  if (isLoading) {
    return (
      <div className="rounded-xl border border-border/70 p-4 space-y-3">
        <Skeleton className="h-5 w-40" />
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-5/6" />
        <div className="grid grid-cols-2 gap-2">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50/40 p-4 space-y-2">
        <p className="text-sm text-red-700">{error}</p>
        <Button size="sm" variant="outline" onClick={onRetry}>Retry Report</Button>
      </div>
    );
  }

  if (!report) {
    return null;
  }

  const summary = report.performance_summary;
  const trend = report.learning_trend || report.trend || "stable";
  const totalScore = typeof summary.total_score === "number" ? summary.total_score : summary.overall_score;
  const totalMax = typeof summary.total_max_score === "number" ? summary.total_max_score : 100;

  return (
    <section className="rounded-2xl border border-border/70 bg-card/80 p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-primary" />
          <h4 className="text-sm font-semibold text-foreground">Session Feedback Report</h4>
        </div>
        <TrendBadge trend={trend} />
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>Performance Summary</span>
          <span>{Math.round(summary.overall_percentage)}% ({Math.round(totalScore)}/{Math.round(totalMax)})</span>
        </div>
        <Progress value={Math.max(0, Math.min(100, summary.overall_percentage || 0))} />
        <p className="text-xs text-muted-foreground">{summary.one_sentence_assessment}</p>
      </div>

      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="rounded-lg border border-green-200 bg-green-50/50 p-2">
          <p className="text-xs text-muted-foreground">Fully Correct</p>
          <p className="text-lg font-semibold text-green-700">{summary.fully_correct_count}</p>
        </div>
        <div className="rounded-lg border border-amber-200 bg-amber-50/50 p-2">
          <p className="text-xs text-muted-foreground">Partial</p>
          <p className="text-lg font-semibold text-amber-700">{summary.partially_correct_count}</p>
        </div>
        <div className="rounded-lg border border-red-200 bg-red-50/50 p-2">
          <p className="text-xs text-muted-foreground">Incorrect</p>
          <p className="text-lg font-semibold text-red-700">{summary.incorrect_count}</p>
        </div>
      </div>

      <div className="space-y-2">
        <p className="text-sm font-semibold text-green-800 flex items-center gap-2">
          <CheckCircle className="w-4 h-4" /> Strength Areas
        </p>
        {report.strength_areas.length === 0 ? (
          <p className="text-xs text-muted-foreground">No strength areas were identified yet.</p>
        ) : (
          <div className="space-y-2">
            {report.strength_areas.map((area, idx) => (
              <div key={`${area.concept}-${idx}`} className="rounded-md border border-green-200 bg-green-50/40 p-2">
                <p className="text-sm font-medium text-foreground">{area.concept}</p>
                <p className="text-xs text-muted-foreground">{area.acknowledgement}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="space-y-2">
        <p className="text-sm font-semibold text-amber-800 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" /> Weak Areas
        </p>
        {report.weak_areas.length === 0 ? (
          <p className="text-xs text-muted-foreground">No weak areas were identified yet.</p>
        ) : (
          <div className="space-y-2">
            {report.weak_areas.map((area, idx) => (
              <div key={`${area.concept}-${idx}`} className="rounded-md border border-amber-200 bg-amber-50/40 p-2">
                <p className="text-sm font-medium text-foreground">{area.concept}</p>
                <p className="text-xs text-muted-foreground">{area.description}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="space-y-2">
        <p className="text-sm font-semibold text-foreground">Improvement Plan</p>
        {report.improvement_plan.length === 0 ? (
          <p className="text-xs text-muted-foreground">No plan items available.</p>
        ) : (
          <div className="space-y-2">
            {report.improvement_plan.map((item, idx) => (
              <div key={`${item.concept}-${idx}`} className="rounded-md border border-border p-2">
                <p className="text-sm font-medium text-foreground">{item.concept}</p>
                <p className="text-xs text-muted-foreground mb-2">{item.study_suggestion}</p>
                <Button size="sm" variant="outline" onClick={() => onAction(item)}>
                  {item.system_action?.label || "Practice Now"}
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="flex items-center gap-2">
        <Button size="sm" onClick={onSave} disabled={isSaved}>{isSaved ? "Saved" : "Save This Report"}</Button>
        <p className="text-xs text-muted-foreground">{report.next_step}</p>
      </div>

      {showDevFooter && (
        <div className="rounded-md border border-dashed border-border px-2 py-1 text-[11px] text-muted-foreground">
          Dev Mode: Session report diagnostics enabled.
        </div>
      )}
    </section>
  );
};
