import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Loader2, HelpCircle, Layers, Network, FileText, Maximize2, Minimize2, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { QuizView } from "@/features/learning/components/QuizView";
import { FlashcardView } from "@/features/learning/components/FlashcardView";
import { SummaryView } from "@/features/learning/components/SummaryView";
import { MindMapTree } from "@/features/learning/components/MindMapTree";
import { SessionReport } from "@/features/learning/components/SessionReport";
import type { SessionFeedbackImprovementItem, SessionFeedbackReport } from "@/lib/notebookApi";

type LearningAidType = "quiz" | "flashcards" | "mindmap" | "summary";

type QuizGenerationFormState = {
  numberOfQuestions: number;
  difficulty: "easy" | "medium" | "hard" | "mixed";
  questionTypes: Array<"mcq" | "short" | "true_false" | "fill_blank">;
  topic: string;
};

type FlashcardGenerationFormState = {
  numberOfCards: number;
  cardMode: "Question->Answer" | "Term->Definition" | "Concept->Explanation";
  topic: string;
};

interface RightPanelProps {
  isOpen: boolean;
  onClose: () => void;
  learningAids: Partial<Record<LearningAidType, any>>;
  aidLoading: LearningAidType | null;
  activeAidTab: LearningAidType | null;
  quizConfig: QuizGenerationFormState;
  onQuizConfigChange: (patch: Partial<QuizGenerationFormState>) => void;
  flashcardConfig: FlashcardGenerationFormState;
  onFlashcardConfigChange: (patch: Partial<FlashcardGenerationFormState>) => void;
  onTabChange: (tab: LearningAidType) => void;
  onRegenerate: (tab: LearningAidType) => void;
  onAddMoreQuestions?: () => void;
  onResetQuizToSettings?: () => void;
  onAddMoreFlashcards?: () => void;
  sessionReport?: SessionFeedbackReport | null;
  sessionReportLoading?: boolean;
  sessionReportError?: string | null;
  sessionReportSaved?: boolean;
  onRetrySessionReport?: () => void;
  onSaveSessionReport?: () => void;
  onRunImprovementAction?: (item: SessionFeedbackImprovementItem) => void;
  onQuizComplete?: (result: {
    totalQuestions: number;
    correctAnswers: number;
    scorePercent: number;
    feedback: string;
    questionResults: Array<{
      question_id?: string;
      question: string;
      question_type?: string;
      concept_tested?: string;
      difficulty?: string;
      concept_tags?: string[];
      score?: number;
      max_score?: number;
      correct_points?: string[];
      incorrect_points?: string[];
      missing_points?: string[];
      reference_answer: string;
      student_answer: string;
      evaluation: Record<string, any>;
      what_you_got_right: string[];
      what_was_incorrect: Array<{ student_claim: string; correction: string }>;
      what_you_missed: string[];
      question_tip: string;
    }>;
  }) => void | Promise<void>;
}

const tabs: { key: LearningAidType; label: string; icon: React.ReactNode }[] = [
  { key: "quiz", label: "Quiz", icon: <HelpCircle className="w-3.5 h-3.5" /> },
  { key: "flashcards", label: "Cards", icon: <Layers className="w-3.5 h-3.5" /> },
  { key: "mindmap", label: "Map", icon: <Network className="w-3.5 h-3.5" /> },
  { key: "summary", label: "Summary", icon: <FileText className="w-3.5 h-3.5" /> },
];

export const RightPanel = ({
  isOpen,
  onClose,
  learningAids,
  aidLoading,
  activeAidTab,
  quizConfig,
  onQuizConfigChange,
  flashcardConfig,
  onFlashcardConfigChange,
  onTabChange,
  onRegenerate,
  onAddMoreQuestions,
  onResetQuizToSettings,
  onAddMoreFlashcards,
  sessionReport,
  sessionReportLoading,
  sessionReportError,
  sessionReportSaved,
  onRetrySessionReport,
  onSaveSessionReport,
  onRunImprovementAction,
  onQuizComplete,
}: RightPanelProps) => {
  const [isFullscreen, setIsFullscreen] = useState(false);

  const toggleQuestionType = (type: QuizGenerationFormState["questionTypes"][number]) => {
    const nextTypes = quizConfig.questionTypes.includes(type)
      ? quizConfig.questionTypes.filter((item) => item !== type)
      : [...quizConfig.questionTypes, type];

    onQuizConfigChange({ questionTypes: nextTypes.length > 0 ? nextTypes : ["mcq"] });
  };

  const toTreeNode = (mindmapPayload: any): any | null => {
    if (!mindmapPayload || typeof mindmapPayload !== "object") return null;

    if (mindmapPayload.label) return mindmapPayload;
    if (mindmapPayload.render_tree?.label) return mindmapPayload.render_tree;

    if (mindmapPayload.mindmap?.central_node?.text) {
      const rootText = String(mindmapPayload.mindmap.central_node.text);
      const branches = Array.isArray(mindmapPayload.mindmap.branches)
        ? mindmapPayload.mindmap.branches
        : [];

      const mapNode = (node: any, fallbackPrefix: string, idx: number) => {
        const label = typeof node?.text === "string" && node.text.trim().length > 0
          ? node.text.trim()
          : `${fallbackPrefix}-${idx + 1}`;

        const subBranches = Array.isArray(node?.sub_branches)
          ? node.sub_branches.map((child: any, childIdx: number) => mapNode(child, "sub", childIdx))
          : [];

        const leafNodes = Array.isArray(node?.leaf_nodes)
          ? node.leaf_nodes.map((leaf: any, leafIdx: number) => ({
            id: String(leaf?.id || `leaf-${idx + 1}-${leafIdx + 1}`),
            label: typeof leaf?.text === "string" && leaf.text.trim().length > 0
              ? leaf.text.trim()
              : `leaf-${leafIdx + 1}`,
            children: [],
          }))
          : [];

        return {
          id: String(node?.id || `${fallbackPrefix}-${idx + 1}`),
          label,
          children: [...subBranches, ...leafNodes],
        };
      };

      return {
        id: "root",
        label: rootText,
        children: branches.map((branch: any, idx: number) => mapNode(branch, "branch", idx)),
      };
    }

    return null;
  };

  const renderQuizPanel = () => {
    const quizQuestions = Array.isArray(learningAids.quiz) ? learningAids.quiz : [];
    const hasQuizData = quizQuestions.length > 0 && !learningAids.quiz?.error;

    return (
      <div className="space-y-4">
        {!hasQuizData && (
          <div className="rounded-2xl border border-border/70 bg-card/80 p-4 space-y-4 shadow-sm">
            <div>
              <p className="text-base font-medium text-foreground">Quiz Settings</p>
              <p className="text-sm text-muted-foreground">
                Choose how many questions to generate and what kind of thinking to target.
              </p>
            </div>

            <div className="grid grid-cols-[1fr_1fr] gap-3">
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">Questions</label>
                <Input
                  type="number"
                  min={3}
                  max={30}
                  value={quizConfig.numberOfQuestions}
                  onChange={(e) => {
                    const nextValue = Number(e.target.value);
                    onQuizConfigChange({
                      numberOfQuestions: Number.isFinite(nextValue) ? Math.max(3, Math.min(30, nextValue)) : 5,
                    });
                  }}
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">Difficulty</label>
                <Select
                  value={quizConfig.difficulty}
                  onValueChange={(value) => onQuizConfigChange({ difficulty: value as QuizGenerationFormState["difficulty"] })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select difficulty" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="easy">Easy</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="hard">Hard</SelectItem>
                    <SelectItem value="mixed">Mixed</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm text-muted-foreground">Question Types</label>
              <div className="flex flex-wrap gap-2">
                {[
                  { key: "mcq", label: "Multiple Choice" },
                  { key: "short", label: "Short Answer" },
                  { key: "true_false", label: "True/False" },
                  { key: "fill_blank", label: "Fill in the Blank" },
                ].map((option) => {
                  const key = option.key as QuizGenerationFormState["questionTypes"][number];
                  const isSelected = quizConfig.questionTypes.includes(key);

                  return (
                    <Button
                      key={option.key}
                      type="button"
                      size="sm"
                      variant={isSelected ? "default" : "outline"}
                      className="rounded-full"
                      onClick={() => toggleQuestionType(key)}
                    >
                      {option.label}
                    </Button>
                  );
                })}
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm text-muted-foreground">Topic/Subtopic Focus (optional)</label>
              <Input
                value={quizConfig.topic}
                onChange={(e) => onQuizConfigChange({ topic: e.target.value })}
                placeholder="e.g. only backpropagation"
              />
            </div>

            <Button className="w-full h-12 text-base" onClick={() => onRegenerate("quiz") }>
              Generate Quiz
            </Button>
          </div>
        )}

        {hasQuizData && (
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" onClick={() => onRegenerate("quiz") }>
              <RefreshCw className="w-3 h-3 mr-2" /> Regenerate
            </Button>
            <Button size="sm" variant="secondary" onClick={() => onAddMoreQuestions?.()} disabled={!onAddMoreQuestions}>
              <HelpCircle className="w-3 h-3 mr-2" /> Add More
            </Button>
            <Button size="sm" variant="ghost" onClick={() => onResetQuizToSettings?.()} disabled={!onResetQuizToSettings}>
              Start Again
            </Button>
          </div>
        )}

        {hasQuizData ? (
          <div className="space-y-4">
            <QuizView questions={quizQuestions} onComplete={onQuizComplete} />
            <SessionReport
              report={sessionReport || null}
              isLoading={Boolean(sessionReportLoading)}
              error={sessionReportError || null}
              isSaved={Boolean(sessionReportSaved)}
              onRetry={() => onRetrySessionReport?.()}
              onSave={() => onSaveSessionReport?.()}
              onAction={(item) => onRunImprovementAction?.(item)}
            />
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
            Generate a quiz using your selected settings.
          </div>
        )}
      </div>
    );
  };

  const renderFlashcardPanel = () => {
    const flashcards = Array.isArray(learningAids.flashcards) ? learningAids.flashcards : [];
    const hasFlashcardData = flashcards.length > 0 && !learningAids.flashcards?.error;

    return (
      <div className="space-y-4">
        {!hasFlashcardData && (
          <div className="rounded-2xl border border-border/70 bg-card/80 p-4 space-y-4 shadow-sm">
            <div>
              <p className="text-base font-medium text-foreground">Flashcard Settings</p>
              <p className="text-sm text-muted-foreground">
                Create flashcards to reinforce key concepts and build long-term retention.
              </p>
            </div>

            <div className="grid grid-cols-[1fr_1fr] gap-3">
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">Flashcards</label>
                <Input
                  type="number"
                  min={5}
                  max={50}
                  value={flashcardConfig.numberOfCards}
                  onChange={(e) => {
                    const nextValue = Number(e.target.value);
                    onFlashcardConfigChange({
                      numberOfCards: Number.isFinite(nextValue) ? Math.max(5, Math.min(50, nextValue)) : 10,
                    });
                  }}
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">Card Mode</label>
                <Select
                  value={flashcardConfig.cardMode}
                  onValueChange={(value) => 
                    onFlashcardConfigChange({ 
                      cardMode: value as FlashcardGenerationFormState["cardMode"] 
                    })
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select mode" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Question->Answer">Question → Answer</SelectItem>
                    <SelectItem value="Term->Definition">Term → Definition</SelectItem>
                    <SelectItem value="Concept->Explanation">Concept → Explanation</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm text-muted-foreground">Topic/Subtopic Focus (optional)</label>
              <Input
                value={flashcardConfig.topic}
                onChange={(e) => onFlashcardConfigChange({ topic: e.target.value })}
                placeholder="e.g. activation functions"
              />
            </div>

            <Button className="w-full h-12 text-base" onClick={() => onRegenerate("flashcards")}>
              Generate Deck
            </Button>
          </div>
        )}

        {hasFlashcardData && (
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" onClick={() => onRegenerate("flashcards")}>
              <RefreshCw className="w-3 h-3 mr-2" /> Regenerate
            </Button>
            <Button size="sm" variant="secondary" onClick={() => onAddMoreFlashcards?.()} disabled={!onAddMoreFlashcards}>
              <Layers className="w-3 h-3 mr-2" /> Add More Cards
            </Button>
          </div>
        )}

        {hasFlashcardData ? (
          <FlashcardView cards={flashcards} />
        ) : (
          <div className="rounded-2xl border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
            Generate a flashcard deck to begin study mode.
          </div>
        )}
      </div>
    );
  };

  const renderContent = () => {
    if (!activeAidTab) {
      return (
        <div className="flex flex-col items-center justify-center h-full text-center py-8 px-4">
          <p className="text-sm text-muted-foreground">
            Select a learning aid from the tabs above or use the <span className="font-medium">🎓</span> button in the chat input.
          </p>
        </div>
      );
    }

    if (aidLoading === activeAidTab) {
      return (
        <div className="flex flex-col items-center justify-center h-full gap-3">
          <Loader2 className="w-6 h-6 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Generating {activeAidTab}...</p>
        </div>
      );
    }

    const data = learningAids[activeAidTab];

    if (!data && activeAidTab !== "quiz" && activeAidTab !== "flashcards") {
      return (
        <div className="flex flex-col items-center justify-center h-full text-center py-8 px-4">
          <p className="text-sm text-muted-foreground">Not generated yet. Click the tab to generate.</p>
        </div>
      );
    }

    if (data?.error) {
      return (
        <div className="flex flex-col items-center justify-center h-full text-center py-8 px-4 gap-4">
          <p className="text-sm text-destructive">{data.error}</p>
          <Button size="sm" variant="outline" onClick={() => onRegenerate(activeAidTab!)}>
            <RefreshCw className="w-3 h-3 mr-2" /> Retry
          </Button>
        </div>
      );
    }

    switch (activeAidTab) {
      case "quiz":
        return renderQuizPanel();
      case "flashcards":
        return renderFlashcardPanel();
      case "mindmap": {
        const treeData = toTreeNode(data);
        return treeData ? (
          <MindMapTree data={treeData} />
        ) : (
          <p className="text-sm text-muted-foreground text-center py-4">Invalid mind map data</p>
        );
      }
      case "summary":
        return <SummaryView content={typeof data === "string" ? data : JSON.stringify(data, null, 2)} />;
      default:
        return null;
    }
  };

  if (isOpen && isFullscreen) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 bg-background flex flex-col"
      >
        <div className="flex-shrink-0 px-6 py-4 border-b border-border flex items-center justify-between">
          <h3 className="font-serif text-xl text-foreground">Learning Aids</h3>
          <div className="flex items-center gap-2">
            <div className="flex bg-muted rounded-lg p-1 mr-4">
              {tabs.map((tab) => {
                const isActive = activeAidTab === tab.key;
                const hasData = !!learningAids[tab.key] && !learningAids[tab.key]?.error;
                const isLoading = aidLoading === tab.key;

                return (
                  <button
                    key={tab.key}
                    onClick={() => onTabChange(tab.key)}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all relative ${
                      isActive
                        ? "bg-background text-primary shadow-sm"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {isLoading ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      tab.icon
                    )}
                    {tab.label}
                    {hasData && !isActive && <span className="w-1.5 h-1.5 rounded-full bg-green-500" />}
                  </button>
                );
              })}
            </div>

            <Button variant="outline" size="icon-sm" onClick={() => setIsFullscreen(false)} title="Exit fullscreen">
              <Minimize2 className="w-4 h-4" />
            </Button>
            <Button variant="ghost" size="icon-sm" onClick={() => { setIsFullscreen(false); onClose(); }}>
              <X className="w-4 h-4" />
            </Button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          <div className="max-w-2xl mx-auto p-8">{renderContent()}</div>
        </div>
      </motion.div>
    );
  }

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
          <div className="p-4 border-b border-border flex items-center justify-between">
            <h3 className="font-serif text-lg text-foreground">Learning Aids</h3>
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="icon-sm" onClick={() => setIsFullscreen(true)} title="Full page view">
                <Maximize2 className="w-3.5 h-3.5" />
              </Button>
              <Button variant="ghost" size="icon-sm" onClick={onClose}>
                <X className="w-4 h-4" />
              </Button>
            </div>
          </div>

          <div className="flex border-b border-border">
            {tabs.map((tab) => {
              const isActive = activeAidTab === tab.key;
              const hasData = !!learningAids[tab.key] && !learningAids[tab.key]?.error;
              const isLoading = aidLoading === tab.key;

              return (
                <button
                  key={tab.key}
                  onClick={() => onTabChange(tab.key)}
                  className={`flex-1 flex flex-col items-center gap-1 py-2.5 text-[10px] font-medium transition-colors relative ${
                    isActive ? "text-primary" : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {isLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : tab.icon}
                  {tab.label}
                  {hasData && <span className="absolute top-1.5 right-2 w-1.5 h-1.5 rounded-full bg-green-500" />}
                  {isActive && (
                    <motion.div
                      layoutId="aid-tab-indicator"
                      className="absolute bottom-0 left-1 right-1 h-0.5 bg-primary rounded-full"
                    />
                  )}
                </button>
              );
            })}
          </div>

          <div className="flex-1 overflow-y-auto p-4 scrollbar-thin">
            {renderContent()}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
