import { motion } from "framer-motion";
import { TrendingUp, TrendingDown, Minus, Target, Brain, AlertCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface FeedbackCardProps {
  type: "strength" | "weakness" | "missed";
  topic: string;
  description: string;
  trend?: "up" | "down" | "stable";
  confidence?: number;
}

const typeConfig = {
  strength: {
    icon: TrendingUp,
    label: "Strength",
    color: "bg-success/10 text-success border-success/20",
    iconColor: "text-success",
  },
  weakness: {
    icon: AlertCircle,
    label: "Needs Work",
    color: "bg-warning/10 text-warning border-warning/20",
    iconColor: "text-warning",
  },
  missed: {
    icon: Brain,
    label: "Missed Concept",
    color: "bg-destructive/10 text-destructive border-destructive/20",
    iconColor: "text-destructive",
  },
};

export const FeedbackCard = ({
  type,
  topic,
  description,
  trend,
  confidence,
}: FeedbackCardProps) => {
  const config = typeConfig[type];
  const Icon = config.icon;

  const TrendIcon = trend === "up" ? TrendingUp : trend === "down" ? TrendingDown : Minus;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.02 }}
      className={`p-4 rounded-xl border ${config.color} transition-all`}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <Icon className={`w-5 h-5 ${config.iconColor}`} />
          <Badge variant="secondary" className="text-xs">
            {config.label}
          </Badge>
        </div>
        {trend && (
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <TrendIcon className="w-3.5 h-3.5" />
            <span>{trend === "up" ? "Improving" : trend === "down" ? "Declining" : "Stable"}</span>
          </div>
        )}
      </div>

      <h4 className="font-serif text-lg text-foreground mb-2">{topic}</h4>
      <p className="text-sm text-muted-foreground mb-3">{description}</p>

      {confidence !== undefined && (
        <div className="flex items-center gap-2">
          <Target className="w-4 h-4 text-muted-foreground" />
          <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-primary"
              initial={{ width: 0 }}
              animate={{ width: `${confidence}%` }}
              transition={{ duration: 0.5, delay: 0.2 }}
            />
          </div>
          <span className="text-xs text-muted-foreground">{confidence}%</span>
        </div>
      )}
    </motion.div>
  );
};
