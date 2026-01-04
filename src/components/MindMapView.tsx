import { useState, useMemo } from "react";
import { motion } from "framer-motion";
import { MindMapNode } from "@/components/MindMapNode";
import { Button } from "@/components/ui/button";
import { ZoomIn, ZoomOut, Maximize2, RotateCcw } from "lucide-react";

interface MindMapData {
  id: string;
  label: string;
  level: number;
  children?: MindMapData[];
}

const mockMindMapData: MindMapData = {
  id: "root",
  label: "Machine Learning",
  level: 0,
  children: [
    {
      id: "supervised",
      label: "Supervised Learning",
      level: 1,
      children: [
        { id: "regression", label: "Regression", level: 2 },
        { id: "classification", label: "Classification", level: 2 },
      ],
    },
    {
      id: "unsupervised",
      label: "Unsupervised Learning",
      level: 1,
      children: [
        { id: "clustering", label: "Clustering", level: 2 },
        { id: "dimensionality", label: "Dim. Reduction", level: 2 },
      ],
    },
    {
      id: "neural",
      label: "Neural Networks",
      level: 1,
      children: [
        { id: "cnn", label: "CNN", level: 2 },
        { id: "rnn", label: "RNN", level: 2 },
        { id: "transformers", label: "Transformers", level: 2 },
      ],
    },
    {
      id: "optimization",
      label: "Optimization",
      level: 1,
      children: [
        { id: "gradient", label: "Gradient Descent", level: 2 },
        { id: "backprop", label: "Backpropagation", level: 2 },
      ],
    },
  ],
};

interface NodePosition {
  id: string;
  label: string;
  level: number;
  x: number;
  y: number;
  parentId?: string;
}

function calculatePositions(
  data: MindMapData,
  centerX: number,
  centerY: number
): { nodes: NodePosition[]; connections: Array<{ from: string; to: string; fromX: number; fromY: number; toX: number; toY: number }> } {
  const nodes: NodePosition[] = [];
  const connections: Array<{ from: string; to: string; fromX: number; fromY: number; toX: number; toY: number }> = [];

  // Root node
  nodes.push({
    id: data.id,
    label: data.label,
    level: 0,
    x: centerX,
    y: centerY,
  });

  // Position children in a circle around root
  if (data.children) {
    const radius1 = 200;
    const angleStep = (2 * Math.PI) / data.children.length;

    data.children.forEach((child, i) => {
      const angle = angleStep * i - Math.PI / 2;
      const x = centerX + radius1 * Math.cos(angle);
      const y = centerY + radius1 * Math.sin(angle);

      nodes.push({
        id: child.id,
        label: child.label,
        level: 1,
        x,
        y,
        parentId: data.id,
      });

      connections.push({
        from: data.id,
        to: child.id,
        fromX: centerX,
        fromY: centerY,
        toX: x,
        toY: y,
      });

      // Position grandchildren
      if (child.children) {
        const radius2 = 120;
        const spreadAngle = Math.PI / 4;
        const childAngleStep = spreadAngle / (child.children.length - 1 || 1);
        const startAngle = angle - spreadAngle / 2;

        child.children.forEach((grandchild, j) => {
          const gAngle = child.children!.length === 1 ? angle : startAngle + childAngleStep * j;
          const gx = x + radius2 * Math.cos(gAngle);
          const gy = y + radius2 * Math.sin(gAngle);

          nodes.push({
            id: grandchild.id,
            label: grandchild.label,
            level: 2,
            x: gx,
            y: gy,
            parentId: child.id,
          });

          connections.push({
            from: child.id,
            to: grandchild.id,
            fromX: x,
            fromY: y,
            toX: gx,
            toY: gy,
          });
        });
      }
    });
  }

  return { nodes, connections };
}

export const MindMapView = () => {
  const [zoom, setZoom] = useState(1);
  const [activeNodeId, setActiveNodeId] = useState<string | null>(null);
  const [pan, setPan] = useState({ x: 0, y: 0 });

  const { nodes, connections } = useMemo(
    () => calculatePositions(mockMindMapData, 500, 400),
    []
  );

  const handleZoomIn = () => setZoom((z) => Math.min(z + 0.2, 2));
  const handleZoomOut = () => setZoom((z) => Math.max(z - 0.2, 0.5));
  const handleReset = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  return (
    <div className="flex-1 relative overflow-hidden bg-background">
      {/* Controls */}
      <div className="absolute top-4 right-4 z-20 flex items-center gap-2">
        <Button variant="glass" size="icon-sm" onClick={handleZoomIn}>
          <ZoomIn className="w-4 h-4" />
        </Button>
        <Button variant="glass" size="icon-sm" onClick={handleZoomOut}>
          <ZoomOut className="w-4 h-4" />
        </Button>
        <Button variant="glass" size="icon-sm" onClick={handleReset}>
          <RotateCcw className="w-4 h-4" />
        </Button>
        <Button variant="glass" size="icon-sm">
          <Maximize2 className="w-4 h-4" />
        </Button>
      </div>

      {/* Header */}
      <div className="absolute top-4 left-4 z-20">
        <h2 className="font-serif text-2xl text-foreground">Concept Mind Map</h2>
        <p className="text-sm text-muted-foreground">Auto-generated from your course materials</p>
      </div>

      {/* Mind Map Canvas */}
      <motion.div
        className="absolute inset-0"
        style={{
          transform: `scale(${zoom}) translate(${pan.x}px, ${pan.y}px)`,
          transformOrigin: "center center",
        }}
        drag
        dragConstraints={{ left: -500, right: 500, top: -500, bottom: 500 }}
        onDrag={(_, info) => {
          setPan((p) => ({ x: p.x + info.delta.x / zoom, y: p.y + info.delta.y / zoom }));
        }}
      >
        {/* SVG for connections */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none">
          <defs>
            <linearGradient id="lineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity="0.6" />
              <stop offset="100%" stopColor="hsl(var(--accent))" stopOpacity="0.3" />
            </linearGradient>
          </defs>
          {connections.map((conn, i) => (
            <motion.line
              key={i}
              x1={conn.fromX}
              y1={conn.fromY}
              x2={conn.toX}
              y2={conn.toY}
              stroke="url(#lineGradient)"
              strokeWidth={2}
              initial={{ pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: 1 }}
              transition={{ duration: 0.5, delay: i * 0.05 }}
            />
          ))}
        </svg>

        {/* Nodes */}
        {nodes.map((node) => (
          <MindMapNode
            key={node.id}
            id={node.id}
            label={node.label}
            level={node.level}
            x={node.x}
            y={node.y}
            isActive={activeNodeId === node.id}
            onClick={() => setActiveNodeId(node.id === activeNodeId ? null : node.id)}
          />
        ))}
      </motion.div>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 z-20 glass-panel p-4">
        <h4 className="text-sm font-medium text-foreground mb-2">Legend</h4>
        <div className="space-y-2 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full bg-primary" />
            <span className="text-muted-foreground">Main Topic</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-secondary" />
            <span className="text-muted-foreground">Subtopic</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-muted" />
            <span className="text-muted-foreground">Concept</span>
          </div>
        </div>
      </div>
    </div>
  );
};
