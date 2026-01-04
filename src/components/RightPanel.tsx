import { motion, AnimatePresence } from "framer-motion";
import { X, FileText, Brain, BarChart3, HelpCircle, Upload, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ResourceItem } from "@/components/ResourceItem";
import { FeedbackCard } from "@/components/FeedbackCard";
import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

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
  resources: Resource[];
  feedback: Feedback[];
  onUploadResource: () => void;
  onResourceClick: (id: string) => void;
  onStartQuiz: () => void;
}

export const RightPanel = ({
  isOpen,
  onClose,
  resources,
  feedback,
  onUploadResource,
  onResourceClick,
  onStartQuiz,
}: RightPanelProps) => {
  const [activeTab, setActiveTab] = useState("resources");

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
            <h3 className="font-serif text-lg text-foreground">Course Tools</h3>
            <Button variant="ghost" size="icon-sm" onClick={onClose}>
              <X className="w-4 h-4" />
            </Button>
          </div>

          {/* Tabs */}
          <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
            <TabsList className="mx-4 mt-4 bg-secondary">
              <TabsTrigger value="resources" className="flex-1 gap-2">
                <FileText className="w-4 h-4" />
                Resources
              </TabsTrigger>
              <TabsTrigger value="feedback" className="flex-1 gap-2">
                <BarChart3 className="w-4 h-4" />
                Feedback
              </TabsTrigger>
            </TabsList>

            {/* Resources Tab */}
            <TabsContent value="resources" className="flex-1 overflow-hidden flex flex-col m-0">
              <div className="p-4 flex-1 overflow-y-auto scrollbar-thin">
                {resources.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-center py-8">
                    <div className="w-16 h-16 rounded-2xl bg-secondary flex items-center justify-center mb-4">
                      <Upload className="w-8 h-8 text-muted-foreground" />
                    </div>
                    <h4 className="font-medium text-foreground mb-2">No resources yet</h4>
                    <p className="text-sm text-muted-foreground mb-4">
                      Upload PDFs, notes, or links to get started
                    </p>
                    <Button onClick={onUploadResource} size="sm">
                      <Plus className="w-4 h-4 mr-2" />
                      Upload Resource
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-1">
                    {resources.map((resource) => (
                      <ResourceItem
                        key={resource.id}
                        {...resource}
                        onClick={() => onResourceClick(resource.id)}
                      />
                    ))}
                  </div>
                )}
              </div>

              {resources.length > 0 && (
                <div className="p-4 border-t border-border">
                  <Button onClick={onUploadResource} variant="outline" className="w-full">
                    <Plus className="w-4 h-4 mr-2" />
                    Add Resource
                  </Button>
                </div>
              )}
            </TabsContent>

            {/* Feedback Tab */}
            <TabsContent value="feedback" className="flex-1 overflow-hidden flex flex-col m-0">
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
            </TabsContent>
          </Tabs>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
