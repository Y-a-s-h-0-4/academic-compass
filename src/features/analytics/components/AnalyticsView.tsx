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
}

const StatCard = ({ title, value, subtitle, icon, trend }: StatCardProps) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    whileHover={{ scale: 1.02 }}
    className="glass-panel-solid p-6"
  >
    <div className="flex items-start justify-between">
      <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
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
  aidGenerations: number;
  studyTimeLabel: string;
}

const TopicProgress = ({ topic, progress, quizzesTaken, aidGenerations, studyTimeLabel }: TopicProgressProps) => (
  <div className="space-y-2">
    <div className="flex items-center justify-between">
      <span className="text-sm font-medium text-foreground">{topic}</span>
      <span className="text-xs text-muted-foreground">{quizzesTaken} quizzes • {aidGenerations} aids • {studyTimeLabel}</span>
    </div>
    <div className="flex items-center gap-3">
      <Progress value={progress} className="flex-1" />
      <span className="text-sm font-medium text-primary w-12 text-right">{progress}%</span>
    </div>
  </div>
);

export type AnalyticsCourseMetric = {
  id: string;
  title: string;
  studySeconds: number;
  quizAttempts: number;
  averageQuizScore: number;
  aidGenerations: number;
  chatCount: number;
};

export type AnalyticsActivityItem = {
  id: string;
  action: string;
  courseName: string;
  createdAt: number;
  score?: number;
};

interface AnalyticsViewProps {
  courses: AnalyticsCourseMetric[];
  recentActivity: AnalyticsActivityItem[];
  totalStudySeconds: number;
  totalAidGenerations: number;
  overallQuizAccuracy: number;
  totalQuizAttempts: number;
}

const formatDuration = (totalSeconds: number) => {
  const safeSeconds = Math.max(0, Math.floor(totalSeconds));
  const hours = Math.floor(safeSeconds / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);

  if (hours <= 0) {
    return `${minutes}m`;
  }

  return `${hours}h ${minutes}m`;
};

const formatRelativeTime = (timestamp: number) => {
  const deltaSeconds = Math.max(0, Math.floor((Date.now() - timestamp) / 1000));
  if (deltaSeconds < 60) return "Just now";
  if (deltaSeconds < 3600) return `${Math.floor(deltaSeconds / 60)}m ago`;
  if (deltaSeconds < 86400) return `${Math.floor(deltaSeconds / 3600)}h ago`;
  return `${Math.floor(deltaSeconds / 86400)}d ago`;
};

export const AnalyticsView = ({
  courses,
  recentActivity,
  totalStudySeconds,
  totalAidGenerations,
  overallQuizAccuracy,
  totalQuizAttempts,
}: AnalyticsViewProps) => {
  const activeCoursesCount = courses.filter(
    (course) => course.studySeconds > 0 || course.aidGenerations > 0 || course.quizAttempts > 0,
  ).length;

  const topicProgress = courses
    .map((course) => {
      const timeScore = Math.min(100, (course.studySeconds / 7200) * 100); // 2h ~= 100%
      const aidScore = Math.min(100, course.aidGenerations * 15);
      const quizScore = Math.max(0, Math.min(100, course.averageQuizScore || 0));
      const composite = Math.round(timeScore * 0.35 + aidScore * 0.25 + quizScore * 0.4);

      return {
        topic: course.title,
        progress: Math.max(0, Math.min(100, composite)),
        quizzesTaken: course.quizAttempts,
        aidGenerations: course.aidGenerations,
        studyTimeLabel: formatDuration(course.studySeconds),
      };
    })
    .sort((a, b) => b.progress - a.progress)
    .slice(0, 8);

  const recentItems = [...recentActivity]
    .sort((a, b) => b.createdAt - a.createdAt)
    .slice(0, 10);

  const stats = [
    {
      title: "Total Study Time",
      value: formatDuration(totalStudySeconds),
      subtitle: "From course timers",
      icon: <Clock className="w-6 h-6 text-primary" />,
    },
    {
      title: "Quiz Accuracy",
      value: `${Math.round(overallQuizAccuracy)}%`,
      subtitle: `${totalQuizAttempts} attempt${totalQuizAttempts === 1 ? "" : "s"}`,
      icon: <Target className="w-6 h-6 text-success" />,
    },
    {
      title: "Learning Aids",
      value: totalAidGenerations,
      subtitle: "Quiz, cards, map, summary",
      icon: <Brain className="w-6 h-6 text-info" />,
    },
    {
      title: "Active Courses",
      value: activeCoursesCount,
      subtitle: `${courses.length} total course${courses.length === 1 ? "" : "s"}`,
      icon: <BookOpen className="w-6 h-6 text-warning" />,
    },
  ];

  const achievements = [
    {
      name: "Starter Focus",
      desc: "Study for at least 10 minutes",
      unlocked: totalStudySeconds >= 600,
    },
    {
      name: "Quiz Explorer",
      desc: "Complete 3 quiz attempts",
      unlocked: totalQuizAttempts >= 3,
    },
    {
      name: "Aid Builder",
      desc: "Generate 5 learning aids",
      unlocked: totalAidGenerations >= 5,
    },
    {
      name: "Deep Focus",
      desc: "Spend 1h on a single course",
      unlocked: courses.some((course) => course.studySeconds >= 3600),
    },
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
                  Course Progress
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-5">
                {topicProgress.length > 0 ? (
                  topicProgress.map((topic) => (
                    <TopicProgress key={topic.topic} {...topic} />
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">
                    No course analytics yet. Start a timer and generate learning aids to build progress.
                  </p>
                )}
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
                  {recentItems.length > 0 ? (
                    recentItems.map((activity, i) => (
                      <motion.div
                        key={activity.id}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.5 + i * 0.1 }}
                        className="flex items-center gap-4 p-3 rounded-lg hover:bg-secondary/50 transition-colors"
                      >
                        <div className="w-10 h-10 rounded-lg bg-secondary flex items-center justify-center">
                          {typeof activity.score === "number" ? (
                            <Award className="w-5 h-5 text-primary" />
                          ) : (
                            <BookOpen className="w-5 h-5 text-muted-foreground" />
                          )}
                        </div>
                        <div className="flex-1">
                          <p className="text-sm font-medium text-foreground">{activity.action}</p>
                          <p className="text-xs text-muted-foreground">{activity.courseName}</p>
                        </div>
                        <div className="text-right">
                          {typeof activity.score === "number" && (
                            <p className="text-sm font-medium text-success">{Math.round(activity.score)}%</p>
                          )}
                          <p className="text-xs text-muted-foreground">{formatRelativeTime(activity.createdAt)}</p>
                        </div>
                      </motion.div>
                    ))
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      Recent learning activity will appear here once you start using quizzes and other learning aids.
                    </p>
                  )}
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
                {achievements.map((achievement, i) => (
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
