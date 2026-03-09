import { motion } from "framer-motion";
import { BookOpen, FileText, Clock, ChevronRight, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface CourseCardProps {
  id: string;
  title: string;
  description: string;
  resourceCount: number;
  resourceLabel?: string;
  lastAccessed?: Date;
  progress?: number;
  onClick: () => void;
  onDelete?: () => void;
}

export const CourseCard = ({
  title,
  description,
  resourceCount,
  resourceLabel = "resources",
  lastAccessed,
  progress = 0,
  onClick,
  onDelete,
}: CourseCardProps) => {
  return (
    <motion.div
      whileHover={{ scale: 1.02, y: -4 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
      className="glass-panel-solid p-6 cursor-pointer group overflow-hidden relative"
    >
      {/* Progress bar */}
      <div className="absolute bottom-0 left-0 right-0 h-1 bg-muted">
        <motion.div
          className="h-full bg-primary"
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.5, delay: 0.2 }}
        />
      </div>

      <div className="flex items-start justify-between mb-4">
        <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
          <BookOpen className="w-6 h-6 text-primary" />
        </div>
        <div className="flex items-center gap-1">
          {onDelete && (
            <Button
              variant="ghost"
              size="icon-sm"
              className="opacity-70 hover:opacity-100"
              onClick={(event) => {
                event.stopPropagation();
                onDelete();
              }}
            >
              <Trash2 className="w-4 h-4 text-destructive" />
            </Button>
          )}
          <motion.div
            className="opacity-0 group-hover:opacity-100 transition-opacity"
            whileHover={{ x: 4 }}
          >
            <ChevronRight className="w-5 h-5 text-muted-foreground" />
          </motion.div>
        </div>
      </div>

      <h3 className="font-serif text-xl text-foreground mb-2 group-hover:text-primary transition-colors">
        {title}
      </h3>
      
      <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
        {description}
      </p>

      <div className="flex items-center gap-4 text-xs text-muted-foreground">
        <div className="flex items-center gap-1.5">
          <FileText className="w-3.5 h-3.5" />
          <span>{resourceCount} {resourceLabel}</span>
        </div>
        {lastAccessed && (
          <div className="flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5" />
            <span>{formatTimeAgo(lastAccessed)}</span>
          </div>
        )}
      </div>

      {progress > 0 && (
        <Badge variant="secondary" className="absolute top-4 right-4 text-xs">
          {progress}% complete
        </Badge>
      )}
    </motion.div>
  );
};

function formatTimeAgo(date: Date): string {
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (days > 0) return `${days}d ago`;
  if (hours > 0) return `${hours}h ago`;
  if (minutes > 0) return `${minutes}m ago`;
  return 'Just now';
}
