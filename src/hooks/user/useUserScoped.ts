/**
 * User-scoped data hooks
 * All data queries automatically filtered by current user ID
 */

import { useUserContext } from "@/context/UserContext";
import { useCallback, useMemo } from "react";

/**
 * Hook for creating user-scoped query parameters
 * Automatically adds userId to all queries
 */
export const useUserScoped = () => {
  const { userId } = useUserContext();

  const addUserContext = useCallback(
    <T extends Record<string, any>>(data: T): T & { userId: string | null } => {
      return {
        ...data,
        userId,
      };
    },
    [userId]
  );

  const filterByUser = useCallback(
    <T extends { userId: string | null }>(items: T[]): T[] => {
      return items.filter((item) => item.userId === userId);
    },
    [userId]
  );

  return {
    userId,
    addUserContext,
    filterByUser,
  };
};

/**
 * Hook for managing user courses
 * Provides CRUD operations scoped to current user
 */
export const useUserCourses = () => {
  const { userId } = useUserContext();

  const createCourse = useCallback(
    async (courseData: any) => {
      const response = await fetch("/api/courses", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...courseData,
          userId,
        }),
      });
      return response.json();
    },
    [userId]
  );

  const getUserCourses = useCallback(async () => {
    const response = await fetch(`/api/courses?userId=${userId}`);
    return response.json();
  }, [userId]);

  const updateCourse = useCallback(
    async (courseId: string, updates: any) => {
      const response = await fetch(`/api/courses/${courseId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...updates,
          userId,
        }),
      });
      return response.json();
    },
    [userId]
  );

  const deleteCourse = useCallback(
    async (courseId: string) => {
      const response = await fetch(`/api/courses/${courseId}?userId=${userId}`, {
        method: "DELETE",
      });
      return response.json();
    },
    [userId]
  );

  return {
    createCourse,
    getUserCourses,
    updateCourse,
    deleteCourse,
  };
};

/**
 * Hook for managing user learning resources
 */
export const useUserResources = () => {
  const { userId } = useUserContext();

  const createResource = useCallback(
    async (resourceData: any) => {
      const response = await fetch("/api/resources", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...resourceData,
          userId,
        }),
      });
      return response.json();
    },
    [userId]
  );

  const getUserResources = useCallback(async () => {
    const response = await fetch(`/api/resources?userId=${userId}`);
    return response.json();
  }, [userId]);

  const updateResource = useCallback(
    async (resourceId: string, updates: any) => {
      const response = await fetch(`/api/resources/${resourceId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...updates,
          userId,
        }),
      });
      return response.json();
    },
    [userId]
  );

  const deleteResource = useCallback(
    async (resourceId: string) => {
      const response = await fetch(
        `/api/resources/${resourceId}?userId=${userId}`,
        {
          method: "DELETE",
        }
      );
      return response.json();
    },
    [userId]
  );

  return {
    createResource,
    getUserResources,
    updateResource,
    deleteResource,
  };
};

/**
 * Hook for managing user quiz results
 */
export const useUserQuizzes = () => {
  const { userId } = useUserContext();

  const submitQuizResult = useCallback(
    async (quizData: any) => {
      const response = await fetch("/api/quizzes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...quizData,
          userId,
        }),
      });
      return response.json();
    },
    [userId]
  );

  const getUserQuizResults = useCallback(async () => {
    const response = await fetch(`/api/quizzes?userId=${userId}`);
    return response.json();
  }, [userId]);

  const getQuizResult = useCallback(
    async (quizId: string) => {
      const response = await fetch(`/api/quizzes/${quizId}?userId=${userId}`);
      return response.json();
    },
    [userId]
  );

  return {
    submitQuizResult,
    getUserQuizResults,
    getQuizResult,
  };
};

/**
 * Hook for managing user feedback
 */
export const useUserFeedback = () => {
  const { userId } = useUserContext();

  const createFeedback = useCallback(
    async (feedbackData: any) => {
      const response = await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...feedbackData,
          userId,
        }),
      });
      return response.json();
    },
    [userId]
  );

  const getUserFeedback = useCallback(async () => {
    const response = await fetch(`/api/feedback?userId=${userId}`);
    return response.json();
  }, [userId]);

  return {
    createFeedback,
    getUserFeedback,
  };
};

/**
 * Hook for managing user chat conversations
 */
export const useUserConversations = () => {
  const { userId } = useUserContext();

  const createConversation = useCallback(
    async (conversationData: any) => {
      const response = await fetch("/api/conversations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...conversationData,
          userId,
        }),
      });
      return response.json();
    },
    [userId]
  );

  const getUserConversations = useCallback(async () => {
    const response = await fetch(`/api/conversations?userId=${userId}`);
    return response.json();
  }, [userId]);

  const updateConversation = useCallback(
    async (conversationId: string, updates: any) => {
      const response = await fetch(`/api/conversations/${conversationId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...updates,
          userId,
        }),
      });
      return response.json();
    },
    [userId]
  );

  const deleteConversation = useCallback(
    async (conversationId: string) => {
      const response = await fetch(
        `/api/conversations/${conversationId}?userId=${userId}`,
        {
          method: "DELETE",
        }
      );
      return response.json();
    },
    [userId]
  );

  return {
    createConversation,
    getUserConversations,
    updateConversation,
    deleteConversation,
  };
};

/**
 * Hook for managing user analytics data
 */
export const useUserAnalytics = () => {
  const { userId } = useUserContext();

  const getUserAnalytics = useCallback(async () => {
    const response = await fetch(`/api/analytics?userId=${userId}`);
    return response.json();
  }, [userId]);

  const getUserStats = useCallback(async () => {
    const response = await fetch(`/api/analytics/stats?userId=${userId}`);
    return response.json();
  }, [userId]);

  return {
    getUserAnalytics,
    getUserStats,
  };
};
