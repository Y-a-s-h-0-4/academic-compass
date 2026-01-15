import { useEffect, useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sidebar } from "@/features/layout/components/Sidebar";
import { RightPanel } from "@/features/layout/components/RightPanel";
import { CourseCard } from "@/features/learning/components/CourseCard";
import { QuizCard } from "@/features/learning/components/QuizCard";
import { MindMapView } from "@/features/mindmap/components/MindMapView";
import { AnalyticsView } from "@/features/analytics/components/AnalyticsView";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { PanelRight, Plus, BookOpen, Send, Loader2, Play, Pause, SkipBack, SkipForward, Mic, MicOff } from "lucide-react";
import UserProfile from "@/components/UserProfile";
import { useUserContext } from "@/context/UserContext";
import {
  ingestSources,
  listSources,
  queryRag,
  queryStream,
  getConversationHistory,
  saveConversationMessage,
} from "@/lib/notebookApi";

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
  const { userId } = useUserContext();
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

  // Notebook API state
  const [sources, setSources] = useState<Array<{ id: string; name: string; path: string; type: string; chunks: number }>>([]);
  const [ingestLoading, setIngestLoading] = useState(false);
  const [ingestMessage, setIngestMessage] = useState<string | null>(null);
  const [webUrl, setWebUrl] = useState("");
  const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null);

  const [queryText, setQueryText] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [citations, setCitations] = useState<Array<Record<string, any>>>([]);
  const [queryLoading, setQueryLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentAudioUrl, setCurrentAudioUrl] = useState<string | null>(null);
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");


  const audioRef = useRef<HTMLAudioElement>(null);
  const mainAudioRef = useRef<HTMLAudioElement>(null);
  const recognitionRef = useRef<any>(null);
  const silenceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const voiceTextRef = useRef<string>("");

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const currentSourcesRef = useRef<Array<Record<string, any>>>([]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load conversation history on mount
  useEffect(() => {
    const loadHistory = async () => {
      if (!userId) {
        console.log("No userId available, skipping history load");
        return;
      }
      
      try {
        console.log("Loading conversation history for user:", userId);
        const history = await getConversationHistory(userId);
        console.log("Loaded history raw response:", history);
        
        // Check if history is an array
        if (!Array.isArray(history)) {
          console.error("History is not an array:", history);
          return;
        }
        
        if (history.length > 0) {
          const loadedMessages = history.map((msg: any) => ({
            id: msg.id || String(Date.now() + Math.random()),
            role: msg.role,
            content: msg.content,
            timestamp: new Date(msg.timestamp || msg.created_at),
            sources: msg.sources,
          }));
          console.log("Setting messages to:", loadedMessages);
          setMessages(loadedMessages);
        } else {
          console.log("No conversation history found");
        }
      } catch (err) {
        console.error("Failed to load conversation history:", err);
      }
    };
    
    loadHistory();
  }, [userId]);

  const handleSendMessage = (content: string) => {
    const userMessage = {
      id: Date.now().toString(),
      role: "user" as const,
      content,
      timestamp: new Date(),
    };
    
    setMessages((prev) => [...prev, userMessage]);

    // Simulate AI response with static "hello" for now
    setTimeout(() => {
      const aiMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant" as const,
        content: "Hello! I understand your question. You can continue speaking or click the mic to stop. The response will be read aloud automatically.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, aiMessage]);
    }, 500);
  };

  // Voice input handler
  const startVoiceInput = () => {
    if (!("webkitSpeechRecognition" in window) && !("SpeechRecognition" in window)) {
      alert("Speech recognition not supported in this browser");
      return;
    }

    const SpeechRecognition = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;

    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    voiceTextRef.current = ""; // Reset voice text

    recognition.onstart = () => {
      setIsListening(true);
      setTranscript("");
      voiceTextRef.current = "";
      setQueryText("");
    };

    recognition.onresult = (event: any) => {
      let finalTranscript = "";
      let interimTranscript = "";
      
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcriptSegment = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcriptSegment + " ";
        } else {
          interimTranscript += transcriptSegment;
        }
      }
      
      // Update the voice text with final results only
      if (finalTranscript) {
        voiceTextRef.current += finalTranscript;
      }
      
      // Display final + interim for real-time feedback
      setQueryText(voiceTextRef.current + interimTranscript);

      // Reset silence timer
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
      
      // Set 2-second silence timeout to auto-submit
      silenceTimerRef.current = setTimeout(() => {
        stopVoiceInput();
        // Auto-submit after 2 seconds of silence
        setTimeout(() => {
          const finalText = voiceTextRef.current.trim();
          if (finalText && userId && sources.length > 0) {
            handleQuerySubmitWithText(finalText);
          }
        }, 100);
      }, 2000); // 2 seconds
    };

    recognition.onerror = (event: any) => {
      console.error("Speech recognition error:", event.error);
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
    };

    recognition.start();
  };

  const stopVoiceInput = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
    setIsListening(false);
    if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
  };

  const handleQuerySubmitWithText = async (text: string) => {
    if (!text.trim()) return;
    if (!userId) {
      setAnswer("Please sign in to ask questions.");
      return;
    }
    if (sources.length === 0) {
      setAnswer("Please upload sources first in the Sources page.");
      return;
    }

    // Add user message to conversation
    const userMessage = {
      id: Date.now().toString(),
      role: "user" as const,
      content: text,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);

    // Save user message to database
    try {
      await saveConversationMessage({
        userId,
        role: "user",
        content: text,
      });
    } catch (err) {
      console.error("Failed to save user message:", err);
    }

    setQueryText("");
    setQueryLoading(true);
    setIsStreaming(true);
    setCitations([]);
    
    // Prepare assistant message placeholder
    const assistantMessageId = (Date.now() + 1).toString();
    let fullAnswer = "";
    currentSourcesRef.current = []; // Reset sources for this query
    
    try {
      // Use streaming API for typewriter effect with TTS
      await queryStream(
        { query: text, user_id: userId, top_k: 8 },
        (char) => {
          // Append character for typewriter effect
          fullAnswer += char;
          setMessages((prev) => {
            const withoutLast = prev.filter(m => m.id !== assistantMessageId);
            return [...withoutLast, {
              id: assistantMessageId,
              role: "assistant" as const,
              content: fullAnswer,
              timestamp: new Date(),
            }];
          });
        },
        (metadata) => {
          // Handle metadata (sources)
          console.log("Metadata:", metadata);
          currentSourcesRef.current = metadata.sources || [];
          setCitations(metadata.sources || []);
        },
        (audioFile) => {
          // Handle audio file - auto-play immediately
          const audioUrl = audioFile.startsWith('http') ? audioFile : `http://localhost:8000${audioFile}`;
          setCurrentAudioUrl(audioUrl);
        },
        () => {
          // Done streaming
          setQueryLoading(false);
          setIsStreaming(false);
          
          // Update with sources
          setMessages((prev) => {
            const withoutLast = prev.filter(m => m.id !== assistantMessageId);
            return [...withoutLast, {
              id: assistantMessageId,
              role: "assistant" as const,
              content: fullAnswer,
              timestamp: new Date(),
              sources: currentSourcesRef.current,
            }];
          });
          
          // Save assistant message to database
          saveConversationMessage({
            userId,
            role: "assistant",
            content: fullAnswer,
            sources: currentSourcesRef.current,
          }).catch((err) => console.error("Failed to save assistant message:", err));
          
          inputRef.current?.focus();
        }
      );
    } catch (err: any) {
      const errorMsg = err?.message || "Query failed";
      setQueryLoading(false);
      setIsStreaming(false);
      
      const errorMessage = {
        id: assistantMessageId,
        role: "assistant" as const,
        content: errorMsg,
        timestamp: new Date(),
      };
      setMessages((prev) => {
        const withoutLast = prev.filter(m => m.id !== assistantMessageId);
        return [...withoutLast, errorMessage];
      });
    }
  };

  const refreshSources = async () => {
    try {
      if (!userId) return;
      const res = await listSources(userId);
      setSources(res.sources || []);
    } catch (err) {
      console.error(err);
    }
  };

  const handleQuerySubmit = async () => {
    handleQuerySubmitWithText(queryText);
  };

  useEffect(() => {
    refreshSources();
  }, [userId]);

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

    if (activePage === "sources") {
      return (
        <div className="flex-1 p-6 overflow-y-auto">
          <div className="max-w-5xl mx-auto space-y-6">
            <div>
              <h1 className="font-serif text-3xl text-foreground mb-2">Sources</h1>
              <p className="text-muted-foreground">Upload documents or ingest a web page to ground answers.</p>
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Ingest</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Input type="file" multiple onChange={(e) => setSelectedFiles(e.target.files)} />
                  <Input
                    placeholder="https://example.com/article"
                    value={webUrl}
                    onChange={(e) => setWebUrl(e.target.value)}
                  />
                  <div className="flex gap-3 items-center">
                    <Button
                      onClick={async () => {
                        try {
                          if (!userId) {
                            setIngestMessage("Please sign in to ingest sources.");
                            return;
                          }
                          setIngestLoading(true);
                          setIngestMessage(null);
                          await ingestSources({
                            files: selectedFiles ? Array.from(selectedFiles) : undefined,
                            webUrl: webUrl || undefined,
                            userId,
                          });
                          setWebUrl("");
                          setSelectedFiles(null);
                          await refreshSources();
                          setIngestMessage("Ingestion started/complete.");
                        } catch (err: any) {
                          setIngestMessage(err?.message || "Failed to ingest");
                        } finally {
                          setIngestLoading(false);
                        }
                      }}
                      disabled={ingestLoading}
                    >
                      {ingestLoading ? "Ingesting..." : "Ingest"}
                    </Button>
                    {ingestMessage && <span className="text-sm text-muted-foreground">{ingestMessage}</span>}
                  </div>
                </div>

                <Separator />

                <div className="space-y-2">
                  <p className="text-sm font-medium text-muted-foreground">Current sources</p>
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    {sources.length === 0 && (
                      <div className="text-sm text-muted-foreground">No sources yet.</div>
                    )}
                    {sources.map((src) => (
                      <div key={src.id} className="border rounded-lg p-3 bg-card shadow-sm">
                        <p className="font-medium text-foreground truncate">{src.name}</p>
                        <p className="text-xs text-muted-foreground">{src.type} • {src.chunks} chunks</p>
                        <p className="text-[11px] text-muted-foreground break-all mt-1">{src.path}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      );
    }

    if (activePage === "home" || activePage.startsWith("course-")) {
      // Map notebook sources to resource format for RightPanel
      const notebookResources = sources.map(src => ({
        id: src.id,
        title: src.name,
        type: (src.type === "pdf" ? "pdf" : src.type === "web" ? "link" : "notes") as "pdf" | "notes" | "slides" | "link",
        uploadedAt: new Date(),
        size: `${src.chunks} chunks`,
        status: "ready" as const,
      }));

      return (
        <>
          <div className="flex-1 flex flex-col overflow-hidden min-h-0">
            {/* Chat Messages Area - Scrollable */}
            <div className="flex-1 overflow-y-auto min-h-0">
              <div className="max-w-3xl mx-auto p-6 space-y-6">
                {messages.length === 0 && (
                  <div className="flex flex-col items-center justify-center min-h-[60vh] text-center py-20">
                    <div className="w-20 h-20 rounded-full bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center mb-6">
                      <BookOpen className="w-10 h-10 text-primary" />
                    </div>
                    <h2 className="font-serif text-2xl text-foreground mb-3">
                      Ask me anything
                    </h2>
                    <p className="text-muted-foreground max-w-md">
                      {!userId
                        ? "Sign in to start asking questions about your documents"
                        : sources.length === 0
                        ? "Upload sources in the Sources page to get started"
                        : "I'll provide answers grounded in your uploaded sources with citations"}
                    </p>
                    {userId && sources.length > 0 && (
                      <div className="mt-6 text-sm text-muted-foreground">
                        💡 {sources.length} source{sources.length !== 1 ? "s" : ""} available
                      </div>
                    )}
                  </div>
                )}

                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                        msg.role === "user"
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted text-foreground"
                      }`}
                    >
                      <p className="text-sm whitespace-pre-wrap leading-relaxed">
                        {msg.content}
                      </p>
                      {msg.sources && msg.sources.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-border/50 space-y-1">
                          <p className="text-xs font-medium opacity-70">Sources:</p>
                          {msg.sources.map((s: any, i: number) => (
                            <div key={i} className="text-xs opacity-70">
                              <span className="font-mono bg-background/20 px-1.5 py-0.5 rounded mr-1.5">
                                [{i + 1}]
                              </span>
                              {s.source_file} {s.page_number ? `(p. ${s.page_number})` : ""}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                {queryLoading && !isStreaming && (
                  <div className="flex justify-start">
                    <div className="bg-muted rounded-2xl px-4 py-3 flex items-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span className="text-sm text-muted-foreground">Thinking...</span>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            </div>

            {/* Input Area - Fixed at bottom */}
            <div className="flex-shrink-0 border-t border-border bg-background/80 backdrop-blur-sm">
              <div className="max-w-3xl mx-auto p-4">
                {!userId && (
                  <div className="mb-3 text-sm text-amber-600 bg-amber-50 dark:bg-amber-950/20 p-3 rounded-lg">
                    Please sign in to ask questions
                  </div>
                )}
                {userId && sources.length === 0 && (
                  <div className="mb-3 text-sm text-blue-600 bg-blue-50 dark:bg-blue-950/20 p-3 rounded-lg">
                    Upload sources in the Sources page to get started
                  </div>
                )}
                
                {/* Hidden audio player - auto-plays without controls */}
                {currentAudioUrl && (
                  <audio 
                    ref={mainAudioRef} 
                    src={currentAudioUrl}
                    autoPlay
                    onEnded={() => setCurrentAudioUrl(null)}
                    className="hidden"
                  />
                )}
                
                <div className="flex items-end gap-3">
                  <Textarea
                    ref={inputRef}
                    placeholder={
                      !userId
                        ? "Sign in to ask questions..."
                        : sources.length === 0
                        ? "Upload sources first..."
                        : isListening
                        ? "Listening... (auto-submit after 2 sec silence)"
                        : "Ask a question about your documents..."
                    }
                    value={queryText}
                    onChange={(e) => setQueryText(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        if (queryText.trim() && !queryLoading && userId && sources.length > 0) {
                          handleQuerySubmit();
                        }
                      }
                    }}
                    disabled={!userId || sources.length === 0 || queryLoading}
                    className="min-h-[52px] max-h-[200px] resize-none"
                    rows={1}
                  />
                  <Button
                    onClick={isListening ? stopVoiceInput : startVoiceInput}
                    disabled={!userId || sources.length === 0}
                    size="icon"
                    className={`h-[52px] w-[52px] flex-shrink-0 ${isListening ? "bg-red-500 hover:bg-red-600" : ""}`}
                    title={isListening ? "Stop listening" : "Start voice input"}
                  >
                    {isListening ? (
                      <MicOff className="w-5 h-5" />
                    ) : (
                      <Mic className="w-5 h-5" />
                    )}
                  </Button>
                  <Button
                    onClick={handleQuerySubmit}
                    disabled={queryLoading || !queryText.trim() || !userId || sources.length === 0}
                    size="icon"
                    className="h-[52px] w-[52px] flex-shrink-0"
                  >
                    {queryLoading ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <Send className="w-5 h-5" />
                    )}
                  </Button>
                </div>
              </div>
            </div>
          </div>
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
    <div className="h-screen bg-background flex overflow-hidden">
      {/* Ambient glow effect */}
      <div 
        className="fixed inset-0 pointer-events-none bg-[radial-gradient(ellipse_at_top_left,hsl(38,92%,50%,0.08),transparent_50%),radial-gradient(ellipse_at_bottom_right,hsl(38,60%,35%,0.05),transparent_50%)]"
      />

      {/* Sidebar */}
      <Sidebar
        activePage={activePage}
        onPageChange={setActivePage}
        courses={mockCourses}
        onAddCourse={() => console.log("Add course")}
      />

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden relative min-h-0">
        <header className="flex-shrink-0 flex items-center justify-between px-6 py-4 border-b border-border bg-background/80 backdrop-blur z-30">
          <div>
            <p className="font-serif text-2xl text-foreground">Academic Compass</p>
            <p className="text-sm text-muted-foreground">Your guided learning companion</p>
          </div>
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              className="hidden sm:inline-flex"
              onClick={() => setActivePage("courses")}
            >
              <BookOpen className="w-4 h-4 mr-2" />
              Courses
            </Button>
            <UserProfile />
          </div>
        </header>

        <AnimatePresence mode="wait">
          <motion.div
            key={activePage}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            className="flex-1 flex overflow-hidden min-h-0"
          >
            {renderContent()}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
};

export default Index;
