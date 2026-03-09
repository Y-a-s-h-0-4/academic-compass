import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Loader2, HelpCircle, Layers, Network, FileText, Maximize2, Minimize2, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { QuizView } from "@/features/learning/components/QuizView";
import { FlashcardView } from "@/features/learning/components/FlashcardView";
import { SummaryView } from "@/features/learning/components/SummaryView";
import { MindMapTree } from "@/features/learning/components/MindMapTree";

type LearningAidType = "quiz" | "flashcards" | "mindmap" | "summary";

interface RightPanelProps {
  isOpen: boolean;
  onClose: () => void;
  learningAids: Partial<Record<LearningAidType, any>>;
  aidLoading: LearningAidType | null;
  activeAidTab: LearningAidType | null;
  onTabChange: (tab: LearningAidType) => void;
  onRegenerate: (tab: LearningAidType) => void;
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
  onTabChange,
  onRegenerate,
}: RightPanelProps) => {
  const [isFullscreen, setIsFullscreen] = useState(false);

  const toTreeNode = (mindmapPayload: any): any | null => {
    if (!mindmapPayload || typeof mindmapPayload !== "object") return null;

    if (mindmapPayload.label) {
      return mindmapPayload;
    }

    if (mindmapPayload.render_tree?.label) {
      return mindmapPayload.render_tree;
    }

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
          <p className="text-sm text-muted-foreground">
            Generating {activeAidTab}...
          </p>
        </div>
      );
    }

    const data = learningAids[activeAidTab];

    if (!data) {
      return (
        <div className="flex flex-col items-center justify-center h-full text-center py-8 px-4">
          <p className="text-sm text-muted-foreground">
            Not generated yet. Click the tab to generate.
          </p>
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
        return <QuizView questions={Array.isArray(data) ? data : []} />;
      case "flashcards":
        return <FlashcardView cards={Array.isArray(data) ? data : []} />;
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

  // Fullscreen overlay
  if (isOpen && isFullscreen) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 bg-background flex flex-col"
      >
        {/* Fullscreen Header */}
        <div className="flex-shrink-0 px-6 py-4 border-b border-border flex items-center justify-between">
          <h3 className="font-serif text-xl text-foreground">Learning Aids</h3>
          <div className="flex items-center gap-2">
            {/* Tabs inline in header for fullscreen */}
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
                    {hasData && !isActive && (
                      <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
                    )}
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

        {/* Fullscreen Content */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-2xl mx-auto p-8">
            {renderContent()}
          </div>
        </div>
      </motion.div>
    );
  }

  // Sidebar mode
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

          {/* Tabs */}
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
                    isActive
                      ? "text-primary"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {isLoading ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    tab.icon
                  )}
                  {tab.label}
                  {hasData && (
                    <span className="absolute top-1.5 right-2 w-1.5 h-1.5 rounded-full bg-green-500" />
                  )}
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

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-4 scrollbar-thin">
            {renderContent()}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
