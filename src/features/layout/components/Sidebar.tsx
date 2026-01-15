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
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useState } from "react";

interface SidebarProps {
  activePage: string;
  onPageChange: (page: string) => void;
  courses: Array<{ id: string; title: string }>;
  onAddCourse: () => void;
}

const navItems = [
  { id: "home", icon: Home, label: "Home" },
  { id: "sources", icon: Database, label: "Sources" },
  { id: "courses", icon: BookOpen, label: "Courses" },
  { id: "mindmap", icon: Brain, label: "Mind Map" },
  { id: "analytics", icon: BarChart3, label: "Analytics" },
];

export const Sidebar = ({ activePage, onPageChange, courses, onAddCourse }: SidebarProps) => {
  const [isCollapsed, setIsCollapsed] = useState(false);

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

        {/* Courses Section */}
        {!isCollapsed && (
          <div className="mt-8">
            <div className="flex items-center justify-between mb-3 px-2">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Your Courses
              </span>
              <Button variant="ghost" size="icon-sm" onClick={onAddCourse}>
                <Plus className="w-4 h-4" />
              </Button>
            </div>
            
            <div className="space-y-1">
              {courses.map((course) => (
                <Button
                  key={course.id}
                  variant="ghost"
                  className="w-full justify-start text-sm font-normal truncate"
                  onClick={() => onPageChange(`course-${course.id}`)}
                >
                  <BookOpen className="w-4 h-4 flex-shrink-0 mr-2" />
                  <span className="truncate">{course.title}</span>
                </Button>
              ))}
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
