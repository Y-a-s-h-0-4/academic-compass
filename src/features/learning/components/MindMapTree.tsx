import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronRight, ChevronDown } from "lucide-react";

interface MindMapNode {
  id: string;
  label: string;
  children?: MindMapNode[];
}

interface MindMapTreeProps {
  data: MindMapNode;
}

const TreeNode = ({ node, depth = 0 }: { node: MindMapNode; depth?: number }) => {
  const [isOpen, setIsOpen] = useState(depth < 2);
  const hasChildren = node.children && node.children.length > 0;

  const colors = [
    "bg-primary/20 text-primary border-primary/30",
    "bg-blue-500/10 text-blue-400 border-blue-500/20",
    "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    "bg-purple-500/10 text-purple-400 border-purple-500/20",
  ];
  const colorClass = colors[Math.min(depth, colors.length - 1)];

  return (
    <div className={depth > 0 ? "ml-4 border-l border-border/50 pl-3" : ""}>
      <motion.button
        className={`flex items-center gap-2 py-1.5 px-2 rounded-md text-xs w-full text-left ${
          hasChildren ? "cursor-pointer hover:bg-muted/50" : ""
        }`}
        onClick={() => hasChildren && setIsOpen(!isOpen)}
        whileTap={hasChildren ? { scale: 0.98 } : {}}
      >
        {hasChildren && (
          isOpen
            ? <ChevronDown className="w-3 h-3 flex-shrink-0 text-muted-foreground" />
            : <ChevronRight className="w-3 h-3 flex-shrink-0 text-muted-foreground" />
        )}
        {!hasChildren && <div className="w-3 h-3 flex-shrink-0" />}
        <span className={`px-2 py-0.5 rounded border text-xs font-medium ${colorClass}`}>
          {node.label}
        </span>
      </motion.button>

      <AnimatePresence>
        {isOpen && hasChildren && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            {node.children!.map((child) => (
              <TreeNode key={child.id} node={child} depth={depth + 1} />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export const MindMapTree = ({ data }: MindMapTreeProps) => {
  return (
    <div className="space-y-1">
      <TreeNode node={data} depth={0} />
    </div>
  );
};
