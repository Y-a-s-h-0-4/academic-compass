import { motion } from "framer-motion";
import { FileText, Link as LinkIcon, Presentation, AudioLines, MoreVertical, Eye } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

type ResourceType = "pdf" | "notes" | "slides" | "audio" | "link";

interface ResourceItemProps {
  id: string;
  title: string;
  type: ResourceType;
  uploadedAt: Date;
  size?: string;
  status: "processing" | "ready" | "error";
  onClick: () => void;
}

const iconMap: Record<ResourceType, React.ReactNode> = {
  pdf: <FileText className="w-5 h-5" />,
  notes: <FileText className="w-5 h-5" />,
  slides: <Presentation className="w-5 h-5" />,
  audio: <AudioLines className="w-5 h-5" />,
  link: <LinkIcon className="w-5 h-5" />,
};

const typeColorMap: Record<ResourceType, string> = {
  pdf: "bg-destructive/10 text-destructive",
  notes: "bg-info/10 text-info",
  slides: "bg-warning/10 text-warning",
  audio: "bg-success/10 text-success",
  link: "bg-primary/10 text-primary",
};

export const ResourceItem = ({
  title,
  type,
  uploadedAt,
  size,
  status,
  onClick,
}: ResourceItemProps) => {
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      whileHover={{ x: 4 }}
      className="flex items-center gap-4 p-3 rounded-lg hover:bg-secondary/50 transition-colors cursor-pointer group"
      onClick={onClick}
    >
      {/* Icon */}
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${typeColorMap[type]}`}>
        {iconMap[type]}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <h4 className="text-sm font-medium text-foreground truncate">{title}</h4>
        <p className="text-xs text-muted-foreground">
          {size && `${size} • `}
          {formatDate(uploadedAt)}
        </p>
      </div>

      {/* Status */}
      {status === "processing" && (
        <Badge variant="secondary" className="animate-pulse">
          Processing...
        </Badge>
      )}
      {status === "error" && (
        <Badge variant="destructive">Error</Badge>
      )}

      {/* Actions */}
      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <Button variant="ghost" size="icon-sm">
          <Eye className="w-4 h-4" />
        </Button>
        <Button variant="ghost" size="icon-sm">
          <MoreVertical className="w-4 h-4" />
        </Button>
      </div>
    </motion.div>
  );
};

function formatDate(date: Date): string {
  return date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}
