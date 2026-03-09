import { motion } from "framer-motion";
import { 
  Home, 
  BookOpen, 
  Brain, 
  BarChart3, 
  Settings, 
  Plus,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Database,
  MoreHorizontal,
  Trash2,
  FolderPlus,
  Pencil,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useState, useRef, useEffect } from "react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface SidebarProps {
  activePage: string;
  onPageChange: (page: string) => void;
  chats: Array<{ id: string; title: string; courseId: string | null }>;
  courses: Array<{ id: string; title: string }>;
  activeChatId: string;
  onAddChat: () => void;
  onSelectChat: (chatId: string) => void;
  onDeleteChat: (chatId: string) => void;
  onRenameChat: (chatId: string, newTitle: string) => void;
  onCreateCourseForChat: (chatId: string) => void;
  onAssignChatToCourse: (chatId: string, courseId: string) => void;
}

const navItems = [
  { id: "home", icon: Home, label: "Home" },
  { id: "sources", icon: Database, label: "Sources" },
  { id: "courses", icon: BookOpen, label: "Courses" },
  { id: "mindmap", icon: Brain, label: "Mind Map" },
  { id: "analytics", icon: BarChart3, label: "Analytics" },
];

export const Sidebar = ({
  activePage,
  onPageChange,
  chats,
  courses,
  activeChatId,
  onAddChat,
  onSelectChat,
  onDeleteChat,
  onRenameChat,
  onCreateCourseForChat,
  onAssignChatToCourse,
}: SidebarProps) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [renamingChatId, setRenamingChatId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const renameInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (renamingChatId) {
      renameInputRef.current?.focus();
      renameInputRef.current?.select();
    }
  }, [renamingChatId]);

  const commitRename = (chatId: string) => {
    const trimmed = renameValue.trim();
    if (trimmed && trimmed !== chats.find(c => c.id === chatId)?.title) {
      onRenameChat(chatId, trimmed);
    }
    setRenamingChatId(null);
  };

  return (
    <motion.aside
      initial={{ x: -100, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      className={`h-screen bg-sidebar flex flex-col border-r border-sidebar-border transition-all duration-300 ${
        isCollapsed ? 'w-20' : 'w-64'
      }`}
    >
      {/* Logo */}
      <div className="p-4 flex items-center justify-between border-b border-sidebar-border">
        <motion.div 
          className="flex items-center gap-3"
          animate={{ opacity: isCollapsed ? 0 : 1, width: isCollapsed ? 0 : 'auto' }}
        >
          <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-primary-foreground" />
          </div>
          {!isCollapsed && (
            <div>
              <h1 className="font-serif text-xl text-foreground">Lumina</h1>
              <p className="text-xs text-muted-foreground">AI Learning Copilot</p>
            </div>
          )}
        </motion.div>
        
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="flex-shrink-0"
        >
          {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </Button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activePage === item.id;

          return (
            <Button
              key={item.id}
              variant={isActive ? "secondary" : "ghost"}
              className={`w-full justify-start gap-3 ${isActive ? 'bg-sidebar-accent text-sidebar-accent-foreground' : ''}`}
              onClick={() => onPageChange(item.id)}
            >
              <Icon className="w-5 h-5 flex-shrink-0" />
              {!isCollapsed && <span>{item.label}</span>}
            </Button>
          );
        })}

        {/* Chats Section */}
        {!isCollapsed && (
          <div className="mt-8">
            <div className="flex items-center justify-between mb-3 px-2">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Your Chats
              </span>
              <Button variant="ghost" size="icon-sm" onClick={onAddChat}>
                <Plus className="w-4 h-4" />
              </Button>
            </div>
            
            <div className="space-y-1">
              {chats.map((chat) => {
                const linkedCourse = courses.find((course) => course.id === chat.courseId);
                const isActiveChat = activePage === "home" && activeChatId === chat.id;

                return (
                  <div key={chat.id} className="flex items-center gap-1">
                    {renamingChatId === chat.id ? (
                      <input
                        ref={renameInputRef}
                        value={renameValue}
                        onChange={(e) => setRenameValue(e.target.value)}
                        onBlur={() => commitRename(chat.id)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") commitRename(chat.id);
                          if (e.key === "Escape") setRenamingChatId(null);
                        }}
                        className="flex-1 text-sm bg-muted border border-border rounded px-2 py-1.5 outline-none focus:ring-1 focus:ring-primary"
                      />
                    ) : (
                      <Button
                        variant={isActiveChat ? "secondary" : "ghost"}
                        className="flex-1 justify-start text-sm font-normal min-w-0"
                        onClick={() => onSelectChat(chat.id)}
                      >
                        <BookOpen className="w-4 h-4 flex-shrink-0 mr-2" />
                        <div className="min-w-0 text-left">
                          <p className="truncate">{chat.title}</p>
                          {linkedCourse && (
                            <p className="text-[10px] text-muted-foreground truncate">
                              in {linkedCourse.title}
                            </p>
                          )}
                        </div>
                      </Button>
                    )}

                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon-sm" className="shrink-0">
                          <MoreHorizontal className="w-4 h-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-56">
                        <DropdownMenuLabel className="truncate">{chat.title}</DropdownMenuLabel>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem onSelect={() => onSelectChat(chat.id)}>
                          Open chat
                        </DropdownMenuItem>
                        <DropdownMenuItem onSelect={() => {
                          setRenameValue(chat.title);
                          setRenamingChatId(chat.id);
                        }}>
                          <Pencil className="w-4 h-4 mr-2" />
                          Rename
                        </DropdownMenuItem>

                        <DropdownMenuSub>
                          <DropdownMenuSubTrigger>
                            <FolderPlus className="w-4 h-4 mr-2" />
                            Organize into course
                          </DropdownMenuSubTrigger>
                          <DropdownMenuSubContent className="w-56">
                            <DropdownMenuItem onSelect={() => onCreateCourseForChat(chat.id)}>
                              Create new course
                            </DropdownMenuItem>
                            <DropdownMenuSub>
                              <DropdownMenuSubTrigger>
                                Add to existing course
                              </DropdownMenuSubTrigger>
                              <DropdownMenuSubContent className="w-56">
                                {courses.length === 0 && (
                                  <DropdownMenuItem disabled>No courses available</DropdownMenuItem>
                                )}
                                {courses.map((course) => (
                                  <DropdownMenuItem
                                    key={course.id}
                                    onSelect={() => onAssignChatToCourse(chat.id, course.id)}
                                  >
                                    {course.title}
                                  </DropdownMenuItem>
                                ))}
                              </DropdownMenuSubContent>
                            </DropdownMenuSub>
                          </DropdownMenuSubContent>
                        </DropdownMenuSub>

                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          onSelect={() => onDeleteChat(chat.id)}
                          className="text-destructive focus:text-destructive"
                        >
                          <Trash2 className="w-4 h-4 mr-2" />
                          Delete chat
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                );
              })}

              {chats.length === 0 && (
                <p className="px-2 text-xs text-muted-foreground">No chats yet</p>
              )}
            </div>
          </div>
        )}
      </nav>

      {/* Settings */}
      <div className="p-4 border-t border-sidebar-border">
        <Button
          variant="ghost"
          className="w-full justify-start gap-3"
          onClick={() => onPageChange("settings")}
        >
          <Settings className="w-5 h-5 flex-shrink-0" />
          {!isCollapsed && <span>Settings</span>}
        </Button>
      </div>
    </motion.aside>
  );
};
