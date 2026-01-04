import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sidebar } from "@/components/Sidebar";
import { ConversationCanvas } from "@/components/ConversationCanvas";
import { RightPanel } from "@/components/RightPanel";
import { CourseCard } from "@/components/CourseCard";
import { QuizCard } from "@/components/QuizCard";
import { MindMapView } from "@/components/MindMapView";
import { AnalyticsView } from "@/components/AnalyticsView";
import { Button } from "@/components/ui/button";
import { 
  PanelRight,
  Plus, 
  GraduationCap,
  Sparkles,
  BookOpen,
  Brain,
  Target
} from "lucide-react";

// Mock data
const mockCourses = [
  { id: "1", title: "Machine Learning Fundamentals" },
  { id: "2", title: "Advanced Algorithms" },
  { id: "3", title: "Data Structures" },
];

const mockResources = [
  { id: "1", title: "Week 1 - Introduction.pdf", type: "pdf" as const, uploadedAt: new Date(), size: "2.4 MB", status: "ready" as const },
  { id: "2", title: "Lecture Notes - Chapter 3", type: "notes" as const, uploadedAt: new Date(Date.now() - 86400000), status: "ready" as const },
  { id: "3", title: "Neural Networks Slides", type: "slides" as const, uploadedAt: new Date(Date.now() - 172800000), size: "5.1 MB", status: "processing" as const },
];

const mockFeedback = [
  { type: "strength" as const, topic: "Linear Algebra", description: "Strong understanding of matrix operations and eigenvalues", trend: "up" as const, confidence: 85 },
  { type: "weakness" as const, topic: "Gradient Descent", description: "Review optimization techniques and learning rates", trend: "stable" as const, confidence: 45 },
  { type: "missed" as const, topic: "Regularization", description: "This concept wasn't covered in recent sessions", confidence: 20 },
];

const mockQuizQuestion = {
  question: "What is the primary purpose of backpropagation in neural networks?",
  options: [
    { id: "a", text: "To initialize the weights randomly", isCorrect: false },
    { id: "b", text: "To calculate gradients for updating weights", isCorrect: true },
    { id: "c", text: "To normalize the input data", isCorrect: false },
    { id: "d", text: "To prevent overfitting", isCorrect: false },
  ],
  explanation: "Backpropagation is used to calculate the gradient of the loss function with respect to each weight, enabling the network to update weights in the direction that minimizes the loss.",
};

const Index = () => {
  const [activePage, setActivePage] = useState("home");
  const [isRightPanelOpen, setIsRightPanelOpen] = useState(true);
  const [showQuiz, setShowQuiz] = useState(false);
  const [messages, setMessages] = useState<Array<{
    id: string;
    role: "user" | "assistant";
    content: string;
    timestamp: Date;
    sources?: Array<{ id: string; title: string; type: "pdf" | "notes" | "slides" | "link"; page?: number }>;
  }>>([]);

  const handleSendMessage = (content: string) => {
    const userMessage = {
      id: Date.now().toString(),
      role: "user" as const,
      content,
      timestamp: new Date(),
    };
    
    setMessages((prev) => [...prev, userMessage]);

    // Simulate AI response
    setTimeout(() => {
      const aiMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant" as const,
        content: "Based on your course materials, I can explain that concept. The key principle here involves understanding the fundamental relationships between the components we discussed in Chapter 3 of your lecture notes. Would you like me to elaborate on any specific aspect?",
        timestamp: new Date(),
        sources: [
          { id: "1", title: "Lecture Notes - Chapter 3", type: "notes" as const, page: 12 },
          { id: "2", title: "Week 1 - Introduction.pdf", type: "pdf" as const, page: 5 },
        ],
      };
      setMessages((prev) => [...prev, aiMessage]);
    }, 1500);
  };

  const renderContent = () => {
    if (showQuiz) {
      return (
        <div className="flex-1 flex items-center justify-center p-8">
          <QuizCard
            {...mockQuizQuestion}
            onAnswer={(optionId, isCorrect) => {
              console.log("Answer:", optionId, "Correct:", isCorrect);
            }}
            onNext={() => setShowQuiz(false)}
          />
        </div>
      );
    }

    if (activePage === "home" || activePage.startsWith("course-")) {
      return (
        <>
          <div className="flex-1 min-w-0">
            <ConversationCanvas
              courseName={activePage.startsWith("course-") ? mockCourses.find(c => `course-${c.id}` === activePage)?.title : undefined}
              messages={messages}
              onSendMessage={handleSendMessage}
            />
          </div>

          {/* Right Panel Toggle */}
          {!isRightPanelOpen && (
            <Button
              variant="glass"
              size="icon"
              className="fixed right-4 top-4 z-50"
              onClick={() => setIsRightPanelOpen(true)}
            >
              <PanelRight className="w-5 h-5" />
            </Button>
          )}

          <RightPanel
            isOpen={isRightPanelOpen}
            onClose={() => setIsRightPanelOpen(false)}
            resources={mockResources}
            feedback={mockFeedback}
            onUploadResource={() => console.log("Upload resource")}
            onResourceClick={(id) => console.log("Resource clicked:", id)}
            onStartQuiz={() => setShowQuiz(true)}
          />
        </>
      );
    }

    if (activePage === "courses") {
      return (
        <div className="flex-1 p-8 overflow-y-auto">
          <div className="max-w-6xl mx-auto">
            <div className="flex items-center justify-between mb-8">
              <div>
                <h1 className="font-serif text-3xl text-foreground mb-2">Your Courses</h1>
                <p className="text-muted-foreground">Manage and explore your learning materials</p>
              </div>
              <Button>
                <Plus className="w-4 h-4 mr-2" />
                New Course
              </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {mockCourses.map((course, index) => (
                <CourseCard
                  key={course.id}
                  id={course.id}
                  title={course.title}
                  description="Explore fundamental concepts and advanced techniques in this comprehensive course."
                  resourceCount={Math.floor(Math.random() * 15) + 5}
                  lastAccessed={new Date(Date.now() - Math.random() * 604800000)}
                  progress={Math.floor(Math.random() * 80) + 10}
                  onClick={() => setActivePage(`course-${course.id}`)}
                />
              ))}
            </div>
          </div>
        </div>
      );
    }

    if (activePage === "mindmap") {
      return <MindMapView />;
    }

    if (activePage === "analytics") {
      return <AnalyticsView />;
    }

    // Default fallback for other pages
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <h2 className="font-serif text-2xl text-foreground mb-2">{activePage}</h2>
          <p className="text-muted-foreground">Coming soon...</p>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-background flex">
      {/* Ambient glow effect */}
      <div 
        className="fixed inset-0 pointer-events-none"
        style={{
          background: 'radial-gradient(ellipse at top left, hsl(38, 92%, 50%, 0.08), transparent 50%), radial-gradient(ellipse at bottom right, hsl(38, 60%, 35%, 0.05), transparent 50%)',
        }}
      />

      {/* Sidebar */}
      <Sidebar
        activePage={activePage}
        onPageChange={setActivePage}
        courses={mockCourses}
        onAddCourse={() => console.log("Add course")}
      />

      {/* Main Content */}
      <main className="flex-1 flex overflow-hidden relative">
        <AnimatePresence mode="wait">
          <motion.div
            key={activePage}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            className="flex-1 flex"
          >
            {renderContent()}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
};

export default Index;
