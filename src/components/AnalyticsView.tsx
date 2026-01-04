import { motion } from "framer-motion";
import { 
  TrendingUp, 
  Clock, 
  Target, 
  Brain, 
  BookOpen, 
  Award,
  Calendar,
  Zap
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  trend?: { value: number; isPositive: boolean };
  color?: string;
}

const StatCard = ({ title, value, subtitle, icon, trend, color = "primary" }: StatCardProps) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    whileHover={{ scale: 1.02 }}
    className="glass-panel-solid p-6"
  >
    <div className="flex items-start justify-between">
      <div className={`w-12 h-12 rounded-xl bg-${color}/10 flex items-center justify-center`}>
        {icon}
      </div>
      {trend && (
        <div className={`flex items-center gap-1 text-xs ${trend.isPositive ? 'text-success' : 'text-destructive'}`}>
          <TrendingUp className={`w-3 h-3 ${!trend.isPositive && 'rotate-180'}`} />
          <span>{trend.value}%</span>
        </div>
      )}
    </div>
    <div className="mt-4">
      <h3 className="text-2xl font-serif text-foreground">{value}</h3>
      <p className="text-sm text-muted-foreground">{title}</p>
      {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
    </div>
  </motion.div>
);

interface TopicProgressProps {
  topic: string;
  progress: number;
  quizzesTaken: number;
}

const TopicProgress = ({ topic, progress, quizzesTaken }: TopicProgressProps) => (
  <div className="space-y-2">
    <div className="flex items-center justify-between">
      <span className="text-sm font-medium text-foreground">{topic}</span>
      <span className="text-xs text-muted-foreground">{quizzesTaken} quizzes</span>
    </div>
    <div className="flex items-center gap-3">
      <Progress value={progress} className="flex-1" />
      <span className="text-sm font-medium text-primary w-12 text-right">{progress}%</span>
    </div>
  </div>
);

export const AnalyticsView = () => {
  const stats = [
    { title: "Total Study Time", value: "24.5h", subtitle: "This week", icon: <Clock className="w-6 h-6 text-primary" />, trend: { value: 12, isPositive: true } },
    { title: "Quiz Accuracy", value: "78%", subtitle: "Last 10 quizzes", icon: <Target className="w-6 h-6 text-success" />, trend: { value: 5, isPositive: true } },
    { title: "Concepts Mastered", value: "32", subtitle: "Out of 48", icon: <Brain className="w-6 h-6 text-info" />, trend: { value: 8, isPositive: true } },
    { title: "Resources Reviewed", value: "15", subtitle: "This month", icon: <BookOpen className="w-6 h-6 text-warning" />, trend: { value: 3, isPositive: true } },
  ];

  const topicProgress = [
    { topic: "Linear Algebra", progress: 85, quizzesTaken: 8 },
    { topic: "Neural Networks", progress: 72, quizzesTaken: 6 },
    { topic: "Optimization", progress: 45, quizzesTaken: 4 },
    { topic: "Probability", progress: 90, quizzesTaken: 10 },
    { topic: "Deep Learning", progress: 38, quizzesTaken: 3 },
  ];

  const recentActivity = [
    { action: "Completed quiz", topic: "Neural Networks", time: "2 hours ago", score: 85 },
    { action: "Reviewed notes", topic: "Backpropagation", time: "5 hours ago" },
    { action: "Asked question", topic: "Gradient Descent", time: "Yesterday" },
    { action: "Completed quiz", topic: "Linear Algebra", time: "2 days ago", score: 92 },
  ];

  return (
    <div className="flex-1 p-8 overflow-y-auto scrollbar-thin">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <div>
          <h1 className="font-serif text-3xl text-foreground mb-2">Learning Analytics</h1>
          <p className="text-muted-foreground">Track your progress and identify areas for improvement</p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {stats.map((stat, i) => (
            <motion.div
              key={stat.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
            >
              <StatCard {...stat} />
            </motion.div>
          ))}
        </div>

        {/* Two Column Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Topic Progress */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 }}
          >
            <Card className="glass-panel-solid border-border/50">
              <CardHeader>
                <CardTitle className="font-serif text-xl flex items-center gap-2">
                  <Zap className="w-5 h-5 text-primary" />
                  Topic Mastery
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-5">
                {topicProgress.map((topic) => (
                  <TopicProgress key={topic.topic} {...topic} />
                ))}
              </CardContent>
            </Card>
          </motion.div>

          {/* Recent Activity */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.4 }}
          >
            <Card className="glass-panel-solid border-border/50">
              <CardHeader>
                <CardTitle className="font-serif text-xl flex items-center gap-2">
                  <Calendar className="w-5 h-5 text-primary" />
                  Recent Activity
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {recentActivity.map((activity, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.5 + i * 0.1 }}
                      className="flex items-center gap-4 p-3 rounded-lg hover:bg-secondary/50 transition-colors"
                    >
                      <div className="w-10 h-10 rounded-lg bg-secondary flex items-center justify-center">
                        {activity.score ? (
                          <Award className="w-5 h-5 text-primary" />
                        ) : (
                          <BookOpen className="w-5 h-5 text-muted-foreground" />
                        )}
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-foreground">{activity.action}</p>
                        <p className="text-xs text-muted-foreground">{activity.topic}</p>
                      </div>
                      <div className="text-right">
                        {activity.score && (
                          <p className="text-sm font-medium text-success">{activity.score}%</p>
                        )}
                        <p className="text-xs text-muted-foreground">{activity.time}</p>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Achievements */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
        >
          <Card className="glass-panel-solid border-border/50">
            <CardHeader>
              <CardTitle className="font-serif text-xl flex items-center gap-2">
                <Award className="w-5 h-5 text-primary" />
                Achievements
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { name: "Quick Learner", desc: "Complete 5 quizzes", unlocked: true },
                  { name: "Perfect Score", desc: "Get 100% on a quiz", unlocked: true },
                  { name: "Consistent", desc: "7 day streak", unlocked: false },
                  { name: "Explorer", desc: "Use all features", unlocked: false },
                ].map((achievement, i) => (
                  <motion.div
                    key={achievement.name}
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: 0.7 + i * 0.1, type: "spring" }}
                    className={`p-4 rounded-xl text-center ${
                      achievement.unlocked 
                        ? 'bg-primary/10 border border-primary/20' 
                        : 'bg-muted/50 border border-border/50 opacity-50'
                    }`}
                  >
                    <div className={`w-12 h-12 rounded-full mx-auto mb-3 flex items-center justify-center ${
                      achievement.unlocked ? 'bg-primary' : 'bg-muted'
                    }`}>
                      <Award className={`w-6 h-6 ${achievement.unlocked ? 'text-primary-foreground' : 'text-muted-foreground'}`} />
                    </div>
                    <h4 className="font-medium text-sm text-foreground">{achievement.name}</h4>
                    <p className="text-xs text-muted-foreground mt-1">{achievement.desc}</p>
                  </motion.div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
};
