import { useEffect, useState, useRef, useCallback } from "react";
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
import { PanelRight, Plus, BookOpen, Send, Loader2, Play, Pause, SkipBack, SkipForward, Mic, MicOff, ArrowDown, Sun, Moon, FileUp, Globe, X, Paperclip, GraduationCap, HelpCircle, Layers, Network, FileText } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import UserProfile from "@/components/UserProfile";
import { useUserContext } from "@/context/UserContext";
import {
  ingestSources,
  listSources,
  queryRag,
  queryStream,
  getConversationHistory,
  saveConversationMessage,
  generateLearningAid,
  LearningAidType,
} from "@/lib/notebookApi";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  sources?: Array<Record<string, any>>;
};

type ChatItem = {
  id: string;
  title: string;
  courseId: string | null;
};

type CourseItem = {
  id: string;
  title: string;
};

type PersistedChatState = {
  chats: ChatItem[];
  courses: CourseItem[];
  activeChatId: string;
};

type MessageContentBlock =
  | { type: "text"; text: string }
  | { type: "table"; headers: string[]; rows: string[][] };

// Mock data
const initialChats: ChatItem[] = [
  { id: "default", title: "Machine Learning Fundamentals", courseId: null },
  { id: "chat-2", title: "Advanced Algorithms", courseId: null },
  { id: "chat-3", title: "Data Structures", courseId: null },
];

const CHAT_STATE_STORAGE_PREFIX = "academic-compass:chat-state:v1";
const NOTEBOOK_API_URL = ((import.meta.env.VITE_NOTEBOOK_API_URL as string | undefined)?.trim() || "").replace(/\/$/, "");

const buildChatMessagesMap = (chatItems: ChatItem[]) =>
  chatItems.reduce((acc, chat) => {
    acc[chat.id] = [];
    return acc;
  }, {} as Record<string, ChatMessage[]>);

const getChatStateStorageKey = (userId?: string | null) =>
  `${CHAT_STATE_STORAGE_PREFIX}:${userId || "anonymous"}`;

const TABLE_SEPARATOR_REGEX = /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/;

const cleanMarkdownCell = (value: string) =>
  value
    .trim()
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/\*(.*?)\*/g, "$1")
    .replace(/`(.*?)`/g, "$1")
    .replace(/\s+/g, " ")
    .trim();

const splitTableRow = (line: string) => {
  let text = line.trim();
  if (text.startsWith("|")) text = text.slice(1);
  if (text.endsWith("|")) text = text.slice(0, -1);
  return text.split("|").map((cell) => cleanMarkdownCell(cell));
};

const toMessageContentBlocks = (content: string): MessageContentBlock[] => {
  const lines = content.split("\n");
  const blocks: MessageContentBlock[] = [];
  const textBuffer: string[] = [];

  const flushText = () => {
    const combined = textBuffer.join("\n").trim();
    if (combined) {
      blocks.push({ type: "text", text: combined });
    }
    textBuffer.length = 0;
  };

  let i = 0;
  while (i < lines.length) {
    const currentLine = lines[i];
    const nextLine = i + 1 < lines.length ? lines[i + 1] : "";
    const isTableStart = currentLine.includes("|") && TABLE_SEPARATOR_REGEX.test(nextLine);

    if (!isTableStart) {
      textBuffer.push(currentLine);
      i += 1;
      continue;
    }

    flushText();

    const headerCells = splitTableRow(currentLine);
    const rowLines: string[] = [];
    i += 2; // Skip header + separator

    while (i < lines.length) {
      const rowLine = lines[i];
      if (!rowLine.includes("|")) break;
      rowLines.push(rowLine);
      i += 1;
    }

    const rowCells = rowLines
      .map((rowLine) => splitTableRow(rowLine))
      .filter((cells) => cells.some((cell) => cell.length > 0));

    const colCount = Math.max(
      headerCells.length,
      ...rowCells.map((cells) => cells.length),
      0,
    );

    if (colCount < 2) {
      // Fallback to text if the structure is too malformed to render as a table.
      textBuffer.push(currentLine, nextLine, ...rowLines);
      continue;
    }

    const normalizedHeaders = Array.from({ length: colCount }, (_, index) => {
      const candidate = headerCells[index] || "";
      return candidate || `Column ${index + 1}`;
    });

    const normalizedRows = rowCells.map((cells) =>
      Array.from({ length: colCount }, (_, index) => cells[index] || "-"),
    );

    blocks.push({
      type: "table",
      headers: normalizedHeaders,
      rows: normalizedRows,
    });
  }

  flushText();

  if (blocks.length === 0 && content.trim()) {
    return [{ type: "text", text: content.trim() }];
  }

  return blocks;
};

const resolveAssetUrl = (assetUrl?: string) => {
  if (!assetUrl) return "";
  if (assetUrl.startsWith("http://") || assetUrl.startsWith("https://")) {
    return assetUrl;
  }
  if (!NOTEBOOK_API_URL) {
    return assetUrl;
  }
  const normalizedPath = assetUrl.startsWith("/") ? assetUrl : `/${assetUrl}`;
  return `${NOTEBOOK_API_URL}${normalizedPath}`;
};

const getVisualReferences = (sources?: Array<Record<string, any>>) => {
  const input = Array.isArray(sources) ? sources : [];
  const visuals: Array<Record<string, any>> = [];
  const seen = new Set<string>();

  for (const source of input) {
    const assetType = source?.asset_type;
    if (assetType !== "image" && assetType !== "table") {
      continue;
    }

    const dedupeKey = [
      assetType,
      source?.asset_url,
      source?.chunk_id,
      source?.reference,
      source?.asset_name,
    ]
      .filter(Boolean)
      .join("|");

    if (dedupeKey && seen.has(dedupeKey)) {
      continue;
    }
    if (dedupeKey) {
      seen.add(dedupeKey);
    }

    visuals.push(source);
  }

  return visuals;
};

const sanitizeChatState = (value: any): PersistedChatState | null => {
  if (!value || typeof value !== "object") return null;

  const rawChats = Array.isArray(value.chats) ? value.chats : [];
  const rawCourses = Array.isArray(value.courses) ? value.courses : [];

  const chats: ChatItem[] = rawChats
    .filter((item: any) => item && typeof item.id === "string" && typeof item.title === "string")
    .map((item: any) => ({
      id: item.id,
      title: item.title,
      courseId: typeof item.courseId === "string" ? item.courseId : null,
    }));

  const courses: CourseItem[] = rawCourses
    .filter((item: any) => item && typeof item.id === "string" && typeof item.title === "string")
    .map((item: any) => ({
      id: item.id,
      title: item.title,
    }));

  if (chats.length === 0) return null;

  const activeChatId = typeof value.activeChatId === "string" ? value.activeChatId : chats[0].id;

  return {
    chats,
    courses,
    activeChatId,
  };
};

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
  const [courses, setCourses] = useState<CourseItem[]>([]);
  const [chats, setChats] = useState<ChatItem[]>(initialChats);
  const [activeChatId, setActiveChatId] = useState(initialChats[0]?.id ?? "");
  const [chatMessagesById, setChatMessagesById] = useState<Record<string, ChatMessage[]>>(
    buildChatMessagesMap(initialChats),
  );
  const [isRightPanelOpen, setIsRightPanelOpen] = useState(true);
  const [showQuiz, setShowQuiz] = useState(false);

  // Notebook API state
  const [sources, setSources] = useState<Array<{ id: string; name: string; path: string; type: string; chunks: number }>>([]);
  const [ingestLoading, setIngestLoading] = useState(false);
  const [ingestMessage, setIngestMessage] = useState<string | null>(null);
  const [webUrl, setWebUrl] = useState("");
  const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null);

  const [queryText, setQueryText] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [showAttachPopover, setShowAttachPopover] = useState(false);
  const [showAidPopover, setShowAidPopover] = useState(false);
  const [learningAids, setLearningAids] = useState<Partial<Record<LearningAidType, any>>>({});
  const [aidLoading, setAidLoading] = useState<LearningAidType | null>(null);
  const [activeAidTab, setActiveAidTab] = useState<LearningAidType | null>(null);
  const [inlineWebUrl, setInlineWebUrl] = useState("");
  const [showUrlInput, setShowUrlInput] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [citations, setCitations] = useState<Array<Record<string, any>>>([]);
  const [queryLoading, setQueryLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentAudioUrl, setCurrentAudioUrl] = useState<string | null>(null);
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [isAtBottom, setIsAtBottom] = useState(true);
  const [theme, setTheme] = useState<"light" | "dark">("dark");

  const audioRef = useRef<HTMLAudioElement>(null);
  const mainAudioRef = useRef<HTMLAudioElement>(null);
  const recognitionRef = useRef<any>(null);
  const silenceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const voiceTextRef = useRef<string>("");

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const currentSourcesRef = useRef<Array<Record<string, any>>>([]);
  const loadedHistoryChatsRef = useRef<Set<string>>(new Set());
  const chatStateHydratedRef = useRef(false);

  const messages = chatMessagesById[activeChatId] || [];

  const setActiveChatMessages = (
    updater: ChatMessage[] | ((prev: ChatMessage[]) => ChatMessage[]),
  ) => {
    if (!activeChatId) return;

    setChatMessagesById((prev) => {
      const current = prev[activeChatId] || [];
      const next = typeof updater === "function"
        ? (updater as (prev: ChatMessage[]) => ChatMessage[])(current)
        : updater;

      return {
        ...prev,
        [activeChatId]: next,
      };
    });
  };

  const resetTransientState = () => {
    setQueryText("");
    setAnswer(null);
    setCitations([]);
    setQueryLoading(false);
    setIsStreaming(false);
    setCurrentAudioUrl(null);
    setTranscript("");
    setSources([]);
    setLearningAids({});
    setAidLoading(null);
    setActiveAidTab(null);

    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }

    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {
        // Ignore if recognition is already stopped.
      }
    }

    setIsListening(false);
    voiceTextRef.current = "";
  };

  const createCourse = (title?: string) => {
    const newCourse: CourseItem = {
      id: `course-${Date.now()}`,
      title: title?.trim() || `New Course ${courses.length + 1}`,
    };

    setCourses((prev) => [newCourse, ...prev]);
    return newCourse;
  };

  const handleAddChat = () => {
    const newChat: ChatItem = {
      id: `chat-${Date.now()}`,
      title: `New Chat ${chats.length + 1}`,
      courseId: null,
    };

    setChats((prev) => [newChat, ...prev]);
    setChatMessagesById((prev) => ({
      ...prev,
      [newChat.id]: [],
    }));
    setActiveChatId(newChat.id);
    setActivePage("home");
    resetTransientState();

    setTimeout(() => {
      inputRef.current?.focus();
    }, 0);
  };

  const handleSelectChat = (chatId: string) => {
    setActiveChatId(chatId);
    setActivePage("home");
    resetTransientState();

    setTimeout(() => {
      inputRef.current?.focus();
    }, 0);
  };

  const handleDeleteChat = (chatId: string) => {
    const remainingChats = chats.filter((chat) => chat.id !== chatId);

    if (remainingChats.length === 0) {
      const fallbackChat: ChatItem = {
        id: `chat-${Date.now()}`,
        title: "New Chat 1",
        courseId: null,
      };

      setChats([fallbackChat]);
      setChatMessagesById((prev) => {
        const next = { ...prev };
        delete next[chatId];
        next[fallbackChat.id] = [];
        return next;
      });
      setActiveChatId(fallbackChat.id);
    } else {
      setChats(remainingChats);
      setChatMessagesById((prev) => {
        const next = { ...prev };
        delete next[chatId];
        return next;
      });

      if (activeChatId === chatId) {
        setActiveChatId(remainingChats[0].id);
      }
    }

    setActivePage("home");
    resetTransientState();
  };

  const handleAddCourse = () => {
    createCourse();
    setActivePage("courses");
  };

  const handleRenameChat = (chatId: string, newTitle: string) => {
    setChats((prev) => prev.map((chat) =>
      chat.id === chatId ? { ...chat, title: newTitle } : chat
    ));
  };

  const handleRenameCourse = (courseId: string, newTitle: string) => {
    setCourses((prev) => prev.map((course) =>
      course.id === courseId ? { ...course, title: newTitle } : course
    ));
  };

  const handleDeleteCourse = (courseId: string) => {
    setCourses((prev) => prev.filter((course) => course.id !== courseId));
    setChats((prev) => prev.map((chat) => (
      chat.courseId === courseId ? { ...chat, courseId: null } : chat
    )));

    if (activePage === `course-${courseId}`) {
      setActivePage("courses");
    }
  };

  const handleCreateCourseForChat = (chatId: string) => {
    const chat = chats.find((item) => item.id === chatId);
    const newCourse = createCourse(chat ? `${chat.title} Course` : undefined);

    setChats((prev) => prev.map((item) => (
      item.id === chatId ? { ...item, courseId: newCourse.id } : item
    )));
    setActivePage("courses");
  };

  const handleAssignChatToCourse = (chatId: string, courseId: string) => {
    setChats((prev) => prev.map((item) => (
      item.id === chatId ? { ...item, courseId } : item
    )));
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    setIsAtBottom(true);
  };

  const handleScroll = useCallback(() => {
    if (!messagesContainerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = messagesContainerRef.current;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
    setIsAtBottom(distanceFromBottom < 100);
  }, []);

  const toggleTheme = () => {
    setTheme((prev) => {
      const next = prev === "dark" ? "light" : "dark";
      document.documentElement.classList.toggle("dark", next === "dark");
      localStorage.setItem("theme", next);
      return next;
    });
  };

  useEffect(() => {
    const storedTheme = localStorage.getItem("theme");
    const initialTheme = storedTheme === "light" || storedTheme === "dark" ? storedTheme : "dark";
    setTheme(initialTheme);
    document.documentElement.classList.toggle("dark", initialTheme === "dark");
  }, []);

  // Hydrate chat metadata from local storage so user-created chats survive refresh/reopen.
  useEffect(() => {
    const storageKey = getChatStateStorageKey(userId);
    const anonymousStorageKey = getChatStateStorageKey(null);
    const fallbackChats = [...initialChats];
    const fallbackCourses: CourseItem[] = [];
    const fallbackActiveChatId = fallbackChats[0]?.id ?? "";

    try {
      let raw = localStorage.getItem(storageKey);

      // If user just signed in and has no user-scoped chat state yet,
      // inherit anonymous state once so chats do not appear to vanish.
      if (!raw && userId) {
        const anonymousRaw = localStorage.getItem(anonymousStorageKey);
        if (anonymousRaw) {
          raw = anonymousRaw;
          localStorage.setItem(storageKey, anonymousRaw);
        }
      }

      const parsed = raw ? sanitizeChatState(JSON.parse(raw)) : null;

      if (parsed) {
        const activeExists = parsed.chats.some((chat) => chat.id === parsed.activeChatId);
        const nextActiveChatId = activeExists ? parsed.activeChatId : parsed.chats[0].id;

        setChats(parsed.chats);
        setCourses(parsed.courses);
        setActiveChatId(nextActiveChatId);
        setChatMessagesById((prev) => {
          const next: Record<string, ChatMessage[]> = {};
          for (const chat of parsed.chats) {
            next[chat.id] = prev[chat.id] || [];
          }
          return next;
        });
      } else {
        setChats(fallbackChats);
        setCourses(fallbackCourses);
        setActiveChatId(fallbackActiveChatId);
        setChatMessagesById((prev) => {
          const next: Record<string, ChatMessage[]> = {};
          for (const chat of fallbackChats) {
            next[chat.id] = prev[chat.id] || [];
          }
          return next;
        });
      }

      loadedHistoryChatsRef.current.clear();
    } catch (error) {
      console.error("Failed to load chat state from local storage:", error);
      setChats(fallbackChats);
      setCourses(fallbackCourses);
      setActiveChatId(fallbackActiveChatId);
      setChatMessagesById(buildChatMessagesMap(fallbackChats));
      loadedHistoryChatsRef.current.clear();
    } finally {
      chatStateHydratedRef.current = true;
    }
  }, [userId]);

  // Persist chat metadata whenever it changes.
  useEffect(() => {
    if (!chatStateHydratedRef.current) return;
    if (!activeChatId || chats.length === 0) return;

    const storageKey = getChatStateStorageKey(userId);
    const payload: PersistedChatState = {
      chats,
      courses,
      activeChatId,
    };

    try {
      localStorage.setItem(storageKey, JSON.stringify(payload));
    } catch (error) {
      console.error("Failed to persist chat state:", error);
    }
  }, [userId, chats, courses, activeChatId]);

  // Keep active chat valid if the chat list changes unexpectedly.
  useEffect(() => {
    if (chats.length === 0) return;
    const exists = chats.some((chat) => chat.id === activeChatId);
    if (!exists) {
      setActiveChatId(chats[0].id);
    }
  }, [chats, activeChatId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (activePage !== "home") return;
    const frame = requestAnimationFrame(() => handleScroll());
    return () => cancelAnimationFrame(frame);
  }, [activePage, messages, handleScroll]);

  // Auto-scroll to latest message when going to home page
  useEffect(() => {
    if (activePage === "home" && messages.length > 0) {
      const timer = setTimeout(() => {
        scrollToBottom();
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [activePage]);

  // Load conversation history once per chat when that chat is first opened.
  useEffect(() => {
    if (!userId || !activeChatId || loadedHistoryChatsRef.current.has(activeChatId)) {
      return;
    }

    const loadHistory = async () => {
      try {
        console.log("Loading conversation history for user:", userId);
        const history = await getConversationHistory(userId, activeChatId);
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
          setChatMessagesById((prev) => ({
            ...prev,
            [activeChatId]: loadedMessages,
          }));
        } else {
          console.log("No conversation history found");
        }
      } catch (err) {
        console.error("Failed to load conversation history:", err);
      } finally {
        loadedHistoryChatsRef.current.add(activeChatId);
      }
    };
    
    loadHistory();
  }, [userId, activeChatId]);

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
          if (finalText && userId && activeChatId && sources.length > 0) {
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
    if (!activeChatId) {
      setAnswer("Create or select a chat first.");
      return;
    }
    if (sources.length === 0) {
      setAnswer("No sources yet. Use the + button to add PDFs, documents, or web links first.");
      return;
    }

    // Add user message to conversation
    const userMessage = {
      id: Date.now().toString(),
      role: "user" as const,
      content: text,
      timestamp: new Date(),
    };
    setActiveChatMessages((prev) => [...prev, userMessage]);

    // Save user message to database
    try {
      await saveConversationMessage({
        userId,
        chatId: activeChatId,
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
        { query: text, user_id: userId, chat_id: activeChatId, top_k: 8 },
        (char) => {
          // Append character for typewriter effect
          fullAnswer += char;
          setActiveChatMessages((prev) => {
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
          setActiveChatMessages((prev) => {
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
            chatId: activeChatId,
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
      setActiveChatMessages((prev) => {
        const withoutLast = prev.filter(m => m.id !== assistantMessageId);
        return [...withoutLast, errorMessage];
      });
    }
  };

  const refreshSources = async () => {
    try {
      if (!userId || !activeChatId) return;
      const res = await listSources(userId, activeChatId);
      setSources(res.sources || []);
    } catch (err) {
      console.error(err);
    }
  };

  const handleIngest = async (files?: File[], url?: string) => {
    try {
      if (!userId) {
        setIngestMessage("Please sign in to ingest sources.");
        return;
      }
      if (!activeChatId) {
        setIngestMessage("Create or select a chat before adding sources.");
        return;
      }

      const hasFiles = Boolean(files && files.length > 0) || Boolean(selectedFiles && selectedFiles.length > 0);
      const hasWebUrl = Boolean(url?.trim()) || Boolean(webUrl.trim());

      if (!hasFiles && !hasWebUrl) {
        setIngestMessage("Add at least one file or a web page URL.");
        return;
      }

      setIngestLoading(true);
      setIngestMessage(null);

      await ingestSources({
        files: files ? Array.from(files) : (selectedFiles ? Array.from(selectedFiles) : undefined),
        webUrl: url?.trim() || webUrl.trim() || undefined,
        userId,
        chatId: activeChatId,
      });

      setWebUrl("");
      setInlineWebUrl("");
      setShowUrlInput(false);
      setSelectedFiles(null);
      await refreshSources();
      setIngestMessage("Sources added successfully!");
    } catch (err: any) {
      setIngestMessage(err?.message || "Failed to ingest");
    } finally {
      setIngestLoading(false);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      setShowAttachPopover(false);
      handleIngest(Array.from(files));
    }
    // Reset so same file can be selected again
    e.target.value = "";
  };

  const handleUrlSubmit = () => {
    if (inlineWebUrl.trim()) {
      setShowAttachPopover(false);
      handleIngest(undefined, inlineWebUrl.trim());
    }
  };

  const handleQuerySubmit = async () => {
    handleQuerySubmitWithText(queryText);
  };

  const handleGenerateAid = async (type: LearningAidType, force = false) => {
    if (!userId || !activeChatId || sources.length === 0) return;
    // If already generated (and not an error), just show the tab
    if (!force && learningAids[type] && !learningAids[type]?.error) {
      setActiveAidTab(type);
      setIsRightPanelOpen(true);
      return;
    }
    setAidLoading(type);
    setActiveAidTab(type);
    setIsRightPanelOpen(true);
    try {
      const result = await generateLearningAid(userId, activeChatId, type);
      // Strip markdown code fences if present
      let raw = (result.content || "").trim();
      raw = raw.replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "").trim();

      let parsed: any;
      try {
        parsed = JSON.parse(raw);
      } catch {
        parsed = raw;
      }

      // Validate the parsed data matches what the component expects
      const isValid =
        (type === "quiz" && Array.isArray(parsed) && parsed.length > 0) ||
        (type === "flashcards" && Array.isArray(parsed) && parsed.length > 0) ||
        (type === "mindmap" && parsed && typeof parsed === "object" && (
          Boolean(parsed.label) ||
          Boolean(parsed?.render_tree?.label) ||
          Boolean(parsed?.mindmap?.central_node?.text)
        )) ||
        (type === "summary" && typeof parsed === "string" && parsed.length > 10);

      if (isValid) {
        setLearningAids((prev) => ({ ...prev, [type]: parsed }));
      } else {
        console.error(`Invalid ${type} data:`, parsed);
        const msg = typeof parsed === "string" && parsed.length > 0 && parsed.length < 200
          ? parsed
          : "Generation returned invalid data. Try again.";
        setLearningAids((prev) => ({ ...prev, [type]: { error: msg } }));
      }
    } catch (err: any) {
      console.error(`Failed to generate ${type}:`, err);
      setLearningAids((prev) => ({ ...prev, [type]: { error: err?.message || "Failed to generate" } }));
    } finally {
      setAidLoading(null);
    }
  };

  useEffect(() => {
    refreshSources();
  }, [userId, activeChatId]);

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
                    <Button onClick={() => handleIngest()} disabled={ingestLoading}>
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
      return (
        <>
          <div className="flex-1 flex flex-col overflow-hidden min-h-0">
            {/* Chat Messages Area - Scrollable */}
            <div 
              ref={messagesContainerRef}
              onScroll={handleScroll}
              className="flex-1 overflow-y-auto min-h-0 relative"
            >
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
                        ? "Use the + button below to add PDFs, slides, or web links"
                        : "I'll provide answers grounded in your uploaded sources with citations"}
                    </p>
                    {userId && sources.length > 0 && (
                      <div className="mt-6 text-sm text-muted-foreground">
                        💡 {sources.length} source{sources.length !== 1 ? "s" : ""} available
                      </div>
                    )}
                  </div>
                )}

                {messages.map((msg) => {
                  const visualSources = getVisualReferences(msg.sources);

                  return (
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
                        <div className="space-y-3">
                          {toMessageContentBlocks(msg.content).map((block, blockIndex) => {
                            if (block.type === "text") {
                              return (
                                <p
                                  key={`text-${msg.id}-${blockIndex}`}
                                  className="text-sm whitespace-pre-wrap leading-relaxed"
                                >
                                  {block.text}
                                </p>
                              );
                            }

                            return (
                              <div
                                key={`table-${msg.id}-${blockIndex}`}
                                className="rounded-xl border border-border/50 overflow-hidden bg-background/60"
                              >
                                <div className="px-3 py-2 text-[11px] font-medium text-muted-foreground border-b border-border/40 bg-muted/30">
                                  Comparison Table
                                </div>
                                <div className="overflow-x-auto">
                                  <table className="min-w-full text-xs">
                                    <thead className="bg-muted/50">
                                      <tr>
                                        {block.headers.map((header, headerIndex) => (
                                          <th
                                            key={`head-${headerIndex}`}
                                            className="px-3 py-2 text-left font-semibold text-foreground border-b border-border/40 whitespace-nowrap"
                                          >
                                            {header}
                                          </th>
                                        ))}
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {block.rows.map((row, rowIndex) => (
                                        <tr
                                          key={`row-${rowIndex}`}
                                          className={rowIndex % 2 === 0 ? "bg-background/70" : "bg-muted/20"}
                                        >
                                          {row.map((cell, cellIndex) => (
                                            <td
                                              key={`cell-${rowIndex}-${cellIndex}`}
                                              className="px-3 py-2 border-b border-border/30 align-top"
                                            >
                                              {cell}
                                            </td>
                                          ))}
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                              </div>
                            );
                          })}
                        </div>

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

                        {visualSources.length > 0 && (
                          <div className="mt-3 pt-3 border-t border-border/50 space-y-2">
                            <p className="text-xs font-medium opacity-70">Extracted Visuals:</p>
                            {visualSources.map((visual, visualIndex) => {
                              if (visual.asset_type === "image") {
                                const imageUrl = resolveAssetUrl(visual.asset_url);
                                if (!imageUrl) {
                                  return null;
                                }

                                return (
                                  <div key={`img-${visual.asset_url || visualIndex}`} className="rounded-lg border border-border/40 p-2 bg-background/40 space-y-1.5">
                                    <p className="text-[11px] text-muted-foreground">
                                      Figure {visualIndex + 1} {visual.page_number ? `(p. ${visual.page_number})` : ""}
                                    </p>
                                    <img
                                      src={imageUrl}
                                      alt={visual.asset_name || `Extracted image ${visualIndex + 1}`}
                                      loading="lazy"
                                      className="w-full max-h-64 object-contain rounded-md border border-border/40 bg-background"
                                    />
                                  </div>
                                );
                              }

                              const tablePreview = typeof visual.table_preview === "string"
                                ? visual.table_preview
                                : "Table extracted from the document.";

                              return (
                                <div key={`table-${visual.asset_url || visualIndex}`} className="rounded-lg border border-border/40 p-2 bg-background/40 space-y-1.5">
                                  <p className="text-[11px] text-muted-foreground">
                                    Table {visual.table_index || visualIndex + 1} {visual.page_number ? `(p. ${visual.page_number})` : ""}
                                  </p>
                                  <pre className="text-[11px] leading-relaxed whitespace-pre-wrap overflow-auto max-h-56 p-2 rounded bg-background border border-border/30">
                                    {tablePreview}
                                  </pre>
                                  {visual.asset_url && (
                                    <a
                                      href={resolveAssetUrl(visual.asset_url)}
                                      target="_blank"
                                      rel="noreferrer"
                                      className="text-[11px] text-primary hover:underline"
                                    >
                                      Open table file
                                    </a>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}

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

              {/* Arrow Button to Scroll Down */}
              <AnimatePresence>
                {!isAtBottom && messages.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 10 }}
                    className="sticky bottom-6 ml-auto mr-6 z-10 w-fit"
                  >
                    <Button
                      onClick={scrollToBottom}
                      size="icon"
                      className="rounded-full shadow-lg bg-primary hover:bg-primary/90"
                    >
                      <ArrowDown className="w-5 h-5" />
                    </Button>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Input Area - Fixed at bottom */}
            <div className="flex-shrink-0 border-t border-border bg-background/80 backdrop-blur-sm">
              <div className="max-w-3xl mx-auto p-4">
                {!userId && (
                  <div className="mb-3 text-sm text-amber-600 bg-amber-50 dark:bg-amber-950/20 p-3 rounded-lg">
                    Please sign in to ask questions
                  </div>
                )}

                {/* Pending file/URL indicator */}
                {ingestLoading && (
                  <div className="mb-3 flex items-center gap-2 text-sm text-primary bg-primary/10 p-3 rounded-lg">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Adding sources...
                  </div>
                )}
                {ingestMessage && !ingestLoading && (
                  <div className="mb-3 text-sm text-muted-foreground bg-muted/50 p-3 rounded-lg flex items-center justify-between">
                    <span>{ingestMessage}</span>
                    <Button variant="ghost" size="icon-sm" onClick={() => setIngestMessage(null)}>
                      <X className="w-3 h-3" />
                    </Button>
                  </div>
                )}

                {/* Inline URL input */}
                {showUrlInput && (
                  <div className="mb-3 flex items-center gap-2">
                    <Globe className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                    <Input
                      placeholder="Paste a URL (article, webpage, etc.)"
                      value={inlineWebUrl}
                      onChange={(e) => setInlineWebUrl(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          handleUrlSubmit();
                        }
                      }}
                      autoFocus
                      className="flex-1"
                    />
                    <Button size="sm" onClick={handleUrlSubmit} disabled={!inlineWebUrl.trim() || ingestLoading}>
                      Add
                    </Button>
                    <Button variant="ghost" size="icon-sm" onClick={() => { setShowUrlInput(false); setInlineWebUrl(""); }}>
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                )}

                {/* Hidden file input */}
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept=".pdf,.ppt,.pptx,.doc,.docx,.txt,.csv,.xlsx"
                  onChange={handleFileSelect}
                  className="hidden"
                />

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
                  {/* Plus button to add sources */}
                  <Popover open={showAttachPopover} onOpenChange={setShowAttachPopover}>
                    <PopoverTrigger asChild>
                      <Button
                        variant="outline"
                        size="icon"
                        className="h-[52px] w-[52px] flex-shrink-0"
                        disabled={!userId || ingestLoading}
                        title="Add files and more"
                      >
                        <Plus className="w-5 h-5" />
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent side="top" align="start" className="w-56 p-2">
                      <div className="space-y-1">
                        <Button
                          variant="ghost"
                          className="w-full justify-start gap-3 text-sm"
                          onClick={() => {
                            setShowAttachPopover(false);
                            fileInputRef.current?.click();
                          }}
                        >
                          <FileUp className="w-4 h-4" />
                          Upload PDF, PPT, Docs
                        </Button>
                        <Button
                          variant="ghost"
                          className="w-full justify-start gap-3 text-sm"
                          onClick={() => {
                            setShowAttachPopover(false);
                            setShowUrlInput(true);
                          }}
                        >
                          <Globe className="w-4 h-4" />
                          Add Web Link
                        </Button>
                      </div>
                    </PopoverContent>
                  </Popover>

                  <Textarea
                    ref={inputRef}
                    placeholder={
                      !userId
                        ? "Sign in to ask questions..."
                        : isListening
                        ? "Listening... (auto-submit after 2 sec silence)"
                        : "Ask a question about your documents..."
                    }
                    value={queryText}
                    onChange={(e) => setQueryText(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        if (queryText.trim() && !queryLoading && userId) {
                          handleQuerySubmit();
                        }
                      }
                    }}
                    disabled={!userId || queryLoading}
                    className="min-h-[52px] max-h-[200px] resize-none"
                    rows={1}
                  />
                  <Button
                    onClick={isListening ? stopVoiceInput : startVoiceInput}
                    disabled={!userId}
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

                  {/* Learning Aid button */}
                  <Popover open={showAidPopover} onOpenChange={setShowAidPopover}>
                    <PopoverTrigger asChild>
                      <Button
                        variant="outline"
                        size="icon"
                        className="h-[52px] w-[52px] flex-shrink-0"
                        disabled={!userId || sources.length === 0}
                        title="Generate learning aids"
                      >
                        <GraduationCap className="w-5 h-5" />
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent side="top" align="end" className="w-56 p-2">
                      <div className="space-y-1">
                        <Button
                          variant="ghost"
                          className="w-full justify-start gap-3 text-sm"
                          disabled={aidLoading !== null}
                          onClick={() => { setShowAidPopover(false); handleGenerateAid("quiz"); }}
                        >
                          <HelpCircle className="w-4 h-4" />
                          Quiz
                          {learningAids.quiz && !learningAids.quiz.error && <span className="ml-auto text-[10px] text-green-500">✓</span>}
                        </Button>
                        <Button
                          variant="ghost"
                          className="w-full justify-start gap-3 text-sm"
                          disabled={aidLoading !== null}
                          onClick={() => { setShowAidPopover(false); handleGenerateAid("flashcards"); }}
                        >
                          <Layers className="w-4 h-4" />
                          Flashcards
                          {learningAids.flashcards && !learningAids.flashcards.error && <span className="ml-auto text-[10px] text-green-500">✓</span>}
                        </Button>
                        <Button
                          variant="ghost"
                          className="w-full justify-start gap-3 text-sm"
                          disabled={aidLoading !== null}
                          onClick={() => { setShowAidPopover(false); handleGenerateAid("mindmap"); }}
                        >
                          <Network className="w-4 h-4" />
                          Mind Map
                          {learningAids.mindmap && !learningAids.mindmap.error && <span className="ml-auto text-[10px] text-green-500">✓</span>}
                        </Button>
                        <Button
                          variant="ghost"
                          className="w-full justify-start gap-3 text-sm"
                          disabled={aidLoading !== null}
                          onClick={() => { setShowAidPopover(false); handleGenerateAid("summary"); }}
                        >
                          <FileText className="w-4 h-4" />
                          Summary
                          {learningAids.summary && !learningAids.summary.error && <span className="ml-auto text-[10px] text-green-500">✓</span>}
                        </Button>
                      </div>
                    </PopoverContent>
                  </Popover>

                  <Button
                    onClick={handleQuerySubmit}
                    disabled={queryLoading || !queryText.trim() || !userId}
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
                <p className="text-muted-foreground">Organize your chats into learning tracks</p>
              </div>
              <Button onClick={handleAddCourse}>
                <Plus className="w-4 h-4 mr-2" />
                New Course
              </Button>
            </div>

            {courses.length === 0 && (
              <div className="rounded-lg border border-dashed border-border p-8 text-center text-muted-foreground">
                No courses yet. Create one, then organize chats from the sidebar menu.
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {courses.map((course) => {
                const chatCount = chats.filter((chat) => chat.courseId === course.id).length;

                return (
                  <CourseCard
                    key={course.id}
                    id={course.id}
                    title={course.title}
                    description="Course folder used to organize related chats."
                    resourceCount={chatCount}
                    resourceLabel={chatCount === 1 ? "chat" : "chats"}
                    lastAccessed={new Date()}
                    progress={0}
                    onClick={() => setActivePage("home")}
                    onDelete={() => handleDeleteCourse(course.id)}
                  />
                );
              })}
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
        chats={chats}
        courses={courses}
        activeChatId={activeChatId}
        onAddChat={handleAddChat}
        onSelectChat={handleSelectChat}
        onDeleteChat={handleDeleteChat}
        onRenameChat={handleRenameChat}
        onCreateCourseForChat={handleCreateCourseForChat}
        onAssignChatToCourse={handleAssignChatToCourse}
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
              size="icon"
              aria-label="Toggle learning aids panel"
              onClick={() => setIsRightPanelOpen((v) => !v)}
              title="Toggle learning aids panel"
            >
              <PanelRight className="w-4 h-4" />
            </Button>
            <Button
              variant="outline"
              size="icon"
              aria-label="Toggle theme"
              onClick={toggleTheme}
            >
              {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </Button>
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

      {/* Right Panel - Learning Aids */}
      <RightPanel
        isOpen={isRightPanelOpen}
        onClose={() => setIsRightPanelOpen(false)}
        learningAids={learningAids}
        aidLoading={aidLoading}
        activeAidTab={activeAidTab}
        onTabChange={(tab) => {
          setActiveAidTab(tab);
          if ((!learningAids[tab] || learningAids[tab]?.error) && userId && sources.length > 0) {
            handleGenerateAid(tab, true);
          }
        }}
        onRegenerate={(tab) => handleGenerateAid(tab, true)}
      />
    </div>
  );
};

export default Index;
