/**
 * Core API types for user-scoped data
 */

/**
 * Base entity type with user ownership
 */
export interface UserOwnedEntity {
  id: string;
  userId: string;
  createdAt: string;
  updatedAt: string;
}

/**
 * Course entity with user scope
 */
export interface Course extends UserOwnedEntity {
  title: string;
  description: string;
  category: string;
  level: "beginner" | "intermediate" | "advanced";
  duration: number; // in minutes
  instructor: string;
  thumbnail?: string;
  progress: number; // 0-100
  enrolled: boolean;
}

/**
 * Learning resource entity
 */
export interface Resource extends UserOwnedEntity {
  title: string;
  description: string;
  type: "article" | "video" | "book" | "course" | "podcast";
  url: string;
  thumbnail?: string;
  duration?: number;
  courseId?: string;
}

/**
 * Quiz result entity
 */
export interface QuizResult extends UserOwnedEntity {
  quizId: string;
  courseId: string;
  score: number;
  totalQuestions: number;
  correctAnswers: number;
  duration: number; // in seconds
  passed: boolean;
}

/**
 * Feedback entity
 */
export interface Feedback extends UserOwnedEntity {
  courseId?: string;
  resourceId?: string;
  rating: number; // 1-5
  comment: string;
  type: "course" | "resource" | "general";
}

/**
 * Conversation message
 */
export interface ConversationMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

/**
 * Conversation entity
 */
export interface Conversation extends UserOwnedEntity {
  title: string;
  topic?: string;
  messages: ConversationMessage[];
  isArchived: boolean;
}

/**
 * Analytics data
 */
export interface UserAnalytics extends UserOwnedEntity {
  totalCoursesEnrolled: number;
  totalCoursesCompleted: number;
  totalLearningTime: number; // in minutes
  averageQuizScore: number;
  totalResourcesViewed: number;
  lastActivityDate: string;
  streakDays: number;
}

/**
 * User profile
 */
export interface UserProfile extends UserOwnedEntity {
  email: string;
  firstName: string;
  lastName: string;
  profileImage?: string;
  bio?: string;
  preferredLanguage: string;
  timezone: string;
  notificationsEnabled: boolean;
}

/**
 * API Response wrapper
 */
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

/**
 * Paginated API response
 */
export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

/**
 * API request options with user context
 */
export interface ApiRequestOptions {
  userId: string;
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  headers?: Record<string, string>;
  body?: any;
}

/**
 * Query filters with user scope
 */
export interface QueryFilters {
  userId: string;
  page?: number;
  pageSize?: number;
  sortBy?: string;
  sortOrder?: "asc" | "desc";
  search?: string;
  filters?: Record<string, any>;
}
