import { motion } from "framer-motion";
import { useState } from "react";

interface MindMapNodeProps {
  id: string;
  label: string;
  level: number;
  x: number;
  y: number;
  isActive?: boolean;
  connections?: string[];
  onClick?: () => void;
}

export const MindMapNode = ({
  label,
  level,
  x,
  y,
  isActive = false,
  onClick,
}: MindMapNodeProps) => {
  const [isHovered, setIsHovered] = useState(false);

  const sizeByLevel: Record<number, string> = {
    0: "w-32 h-32",
    1: "w-24 h-24",
    2: "w-20 h-20",
    3: "w-16 h-16",
  };

  const size = sizeByLevel[level] || sizeByLevel[3];

  return (
    <motion.div
      className={`absolute flex items-center justify-center rounded-full cursor-pointer transition-all duration-300 ${size} ${
        level === 0
          ? 'bg-primary text-primary-foreground shadow-glow'
          : isActive
          ? 'bg-accent text-accent-foreground border-2 border-primary'
          : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
      }`}
      style={{ left: x, top: y, transform: 'translate(-50%, -50%)' }}
      initial={{ scale: 0, opacity: 0 }}
      animate={{ 
        scale: isHovered ? 1.1 : 1, 
        opacity: 1,
        boxShadow: isHovered ? '0 0 30px hsl(var(--primary) / 0.4)' : 'none'
      }}
      transition={{ 
        type: "spring", 
        stiffness: 300, 
        damping: 20,
        delay: level * 0.1 
      }}
      onHoverStart={() => setIsHovered(true)}
      onHoverEnd={() => setIsHovered(false)}
      onClick={onClick}
    >
      <span className={`text-center font-medium leading-tight px-2 ${
        level === 0 ? 'text-sm' : 'text-xs'
      }`}>
        {label}
      </span>
    </motion.div>
  );
};
