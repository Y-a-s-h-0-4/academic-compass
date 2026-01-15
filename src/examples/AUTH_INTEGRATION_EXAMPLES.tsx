/**
 * Example: Integrating User Context into Existing Features
 * 
 * This file demonstrates how to update existing components and features
 * to use the new Clerk authentication system with user-scoped data.
 */

// ============================================================================
// EXAMPLE 1: Update a Feature Component with User Context
// ============================================================================

import { useUserContext } from "@/context/UserContext";
import { useUserCourses } from "@/hooks/user";
import { Course } from "@/types/api";
import { useEffect, useState } from "react";

/**
 * Example: Course List Component with User Context
 */
export const CourseListExample = () => {
  const { userId, firstName } = useUserContext();
  const { getUserCourses } = useUserCourses();
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchCourses = async () => {
      try {
        setLoading(true);
        // Data is automatically scoped to current user
        const data = await getUserCourses();
        setCourses(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load courses");
      } finally {
        setLoading(false);
      }
    };

    fetchCourses();
  }, [userId, getUserCourses]);

  if (loading) return <div>Loading courses...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      <h1>Welcome back, {firstName}!</h1>
      <p>Your enrolled courses:</p>
      <ul>
        {courses.map((course) => (
          <li key={course.id}>
            <h3>{course.title}</h3>
            <p>Progress: {course.progress}%</p>
          </li>
        ))}
      </ul>
    </div>
  );
};

// ============================================================================
// EXAMPLE 2: Create a New Resource with User Context
// ============================================================================

import { useUserResources } from "@/hooks/user";

export const ResourceCreationExample = () => {
  const { userId } = useUserContext();
  const { createResource } = useUserResources();

  const handleCreateResource = async () => {
    try {
      // userId is automatically included
      const newResource = await createResource({
        title: "New Resource",
        description: "A learning resource",
        type: "article",
        url: "https://example.com",
        courseId: "course-123",
      });

      console.log("Resource created:", newResource);
      // Resource now has userId field automatically set to current user
    } catch (error) {
      console.error("Failed to create resource:", error);
    }
  };

  return (
    <button onClick={handleCreateResource}>
      Create Resource
    </button>
  );
};

// ============================================================================
// EXAMPLE 3: Use API Client with User Context
// ============================================================================

import { useApiClient, buildApiUrl } from "@/lib/api-client";

export const ApiClientExample = () => {
  const { userId } = useUserContext();
  const { get, post } = useApiClient();

  const fetchAnalytics = async () => {
    try {
      // buildApiUrl automatically adds userId
      const url = buildApiUrl("/analytics", userId!);
      const analytics = await get(url);
      console.log("User analytics:", analytics);
    } catch (error) {
      console.error("Failed to fetch analytics:", error);
    }
  };

  const submitQuizResult = async (quizData: any) => {
    try {
      const url = buildApiUrl("/quizzes", userId!);
      const result = await post(url, {
        ...quizData,
        // userId is already in the URL and headers
      });
      console.log("Quiz result submitted:", result);
    } catch (error) {
      console.error("Failed to submit quiz:", error);
    }
  };

  return (
    <div>
      <button onClick={fetchAnalytics}>Load Analytics</button>
      <button onClick={() => submitQuizResult({ score: 95 })}>
        Submit Quiz
      </button>
    </div>
  );
};

// ============================================================================
// EXAMPLE 4: Protected Feature Component
// ============================================================================

import { ProtectedRoute } from "@/components/ProtectedRoute";
import { useAuth } from "@clerk/clerk-react";

export const ProtectedFeatureExample = () => {
  const { isLoaded, isSignedIn } = useAuth();

  if (!isLoaded) return <div>Loading...</div>;

  return (
    <ProtectedRoute>
      <div>
        <h1>This content is only visible to authenticated users</h1>
        <p>If you're seeing this, you're signed in!</p>
      </div>
    </ProtectedRoute>
  );
};

// ============================================================================
// EXAMPLE 5: Update Existing Feature to Use User Context
// ============================================================================

/**
 * Before: Component without user context
 */
const OldComponentExample = () => {
  const [courses, setCourses] = useState([]);

  useEffect(() => {
    // Problem: Gets all courses, not scoped to user
    fetch("/api/courses")
      .then((r) => r.json())
      .then(setCourses);
  }, []);

  return <div>{courses.map((c: any) => <div key={c.id}>{c.title}</div>)}</div>;
};

/**
 * After: Component with user context
 */
const NewComponentExample = () => {
  const { userId } = useUserContext();
  const { getUserCourses } = useUserCourses();
  const [courses, setCourses] = useState<Course[]>([]);

  useEffect(() => {
    // Solution: Gets only user's courses, automatically scoped
    getUserCourses().then(setCourses);
  }, [userId, getUserCourses]);

  return <div>{courses.map((c) => <div key={c.id}>{c.title}</div>)}</div>;
};

// ============================================================================
// EXAMPLE 6: Custom Hook for Feature-Specific User Data
// ============================================================================

/**
 * Create feature-specific hooks that combine user context and data fetching
 */
export const useFeatureData = () => {
  const { userId } = useUserContext();
  const { getUserCourses, createCourse } = useUserCourses();
  const { getUserResources, createResource } = useUserResources();
  const { getUserAnalytics } = useUserAnalytics();

  // Combined hook for a feature that needs multiple data types
  const fetchFeatureData = async () => {
    const [courses, resources, analytics] = await Promise.all([
      getUserCourses(),
      getUserResources(),
      getUserAnalytics(),
    ]);

    return {
      courses,
      resources,
      analytics,
      userId, // Include userId if needed for comparisons
    };
  };

  return {
    fetchFeatureData,
    createCourse,
    createResource,
  };
};

// ============================================================================
// EXAMPLE 7: Display User Profile with User Context
// ============================================================================

import { UserProfile } from "@/components/UserProfile";

export const ProfileHeaderExample = () => {
  const { email, isSignedIn } = useUserContext();

  return (
    <div className="flex justify-between items-center p-4 bg-white shadow">
      <h1>Academic Compass</h1>
      {isSignedIn && (
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-600">{email}</span>
          <UserProfile />
        </div>
      )}
    </div>
  );
};

// ============================================================================
// EXAMPLE 8: Backend Integration Pattern
// ============================================================================

/**
 * Example backend endpoint that validates user context
 * 
 * // In your backend (Node.js/Express example):
 * 
 * app.get("/api/courses", async (req, res) => {
 *   const { userId } = req.query;
 *   const token = req.headers.authorization?.split("Bearer ")[1];
 * 
 *   // Verify token and extract user ID from Clerk
 *   const clerkUserId = await verifyClerkToken(token);
 * 
 *   // Ensure user can only access their own data
 *   if (userId !== clerkUserId) {
 *     return res.status(403).json({ error: "Unauthorized" });
 *   }
 * 
 *   // Fetch user's courses from database
 *   const courses = await db.courses.find({ userId });
 *   res.json(courses);
 * });
 */

// ============================================================================
// EXAMPLE 9: Handling Authentication Errors
// ============================================================================

import { handleApiError, validateUserContext } from "@/middleware/auth-middleware";

export const ErrorHandlingExample = async () => {
  try {
    const { userId } = useUserContext();

    // Validate user context exists
    validateUserContext(userId);

    // Make API request
    const response = await fetch("/api/courses", {
      method: "GET",
      headers: {
        "X-User-Id": userId || "",
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    // Handle errors with user context awareness
    handleApiError(error);
  }
};

// ============================================================================
// EXAMPLE 10: Logout and Cleanup
// ============================================================================

export const LogoutExample = () => {
  const { logout } = useUserContext();

  const handleLogout = async () => {
    try {
      // Perform cleanup if needed
      // - Clear cached data
      // - Close WebSocket connections
      // - Save user preferences
      console.log("Clearing user data...");

      // Then logout
      await logout();

      // User will be redirected to sign-in
    } catch (error) {
      console.error("Logout failed:", error);
    }
  };

  return <button onClick={handleLogout}>Sign Out</button>;
};

// ============================================================================
// Import for useUserAnalytics needed in Example 6
// ============================================================================

import { useUserAnalytics } from "@/hooks/user";

export {};
