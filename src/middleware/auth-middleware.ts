/**
 * Request interceptor and middleware for user context
 * Automatically adds userId and auth token to all API requests
 */

import { useUserContext } from "@/context/UserContext";
import { useAuth } from "@clerk/clerk-react";
import { useCallback } from "react";

/**
 * Hook for creating request interceptor with user context
 */
export const useRequestInterceptor = () => {
  const { userId } = useUserContext();
  const { getToken } = useAuth();

  const intercept = useCallback(
    async (config: RequestInit & { url?: string }): Promise<RequestInit> => {
      const token = await getToken();

      return {
        ...config,
        headers: {
          "Content-Type": "application/json",
          ...(token && { Authorization: `Bearer ${token}` }),
          "X-User-Id": userId || "",
          ...config.headers,
        },
      };
    },
    [userId, getToken]
  );

  return { intercept };
};

/**
 * Response error handler with user context validation
 */
export const handleApiError = (error: any): never => {
  if (error.response) {
    // Server responded with error status
    const status = error.response.status;
    const data = error.response.data;

    switch (status) {
      case 401:
        // Unauthorized - user not authenticated
        throw new Error("Authentication required. Please sign in.");
      case 403:
        // Forbidden - user not authorized for this resource
        throw new Error("You don't have permission to access this resource.");
      case 404:
        // Not found
        throw new Error("Resource not found.");
      case 422:
        // Validation error
        throw new Error(data.message || "Invalid request data.");
      case 429:
        // Rate limited
        throw new Error("Too many requests. Please try again later.");
      case 500:
        // Server error
        throw new Error("Server error. Please try again later.");
      default:
        throw new Error(data.message || `Error: ${status}`);
    }
  } else if (error.request) {
    // Request made but no response
    throw new Error("Network error. Please check your connection.");
  } else {
    // Other errors
    throw new Error(error.message || "Unknown error occurred.");
  }
};

/**
 * Middleware for validating user context in requests
 */
export const validateUserContext = (userId: string | null): void => {
  if (!userId) {
    throw new Error("User context is missing. Please sign in.");
  }
};

/**
 * Middleware for checking user permissions
 */
export const checkUserPermission = (
  requestUserId: string | null,
  resourceUserId: string | null
): void => {
  if (requestUserId !== resourceUserId) {
    throw new Error("You don't have permission to access this resource.");
  }
};

/**
 * Hook for request/response logging with user context
 */
export const useRequestLogger = () => {
  const { userId } = useUserContext();

  const logRequest = useCallback(
    (method: string, url: string, data?: any) => {
      if (process.env.NODE_ENV === "development") {
        console.log(`[API] ${method} ${url}`, {
          userId,
          data: data ? JSON.parse(JSON.stringify(data)) : undefined,
          timestamp: new Date().toISOString(),
        });
      }
    },
    [userId]
  );

  const logResponse = useCallback(
    (method: string, url: string, status: number, response?: any) => {
      if (process.env.NODE_ENV === "development") {
        console.log(`[API] ${method} ${url} → ${status}`, {
          userId,
          response: response ? JSON.parse(JSON.stringify(response)) : undefined,
          timestamp: new Date().toISOString(),
        });
      }
    },
    [userId]
  );

  const logError = useCallback(
    (method: string, url: string, error: any) => {
      console.error(`[API Error] ${method} ${url}`, {
        userId,
        error: error.message,
        timestamp: new Date().toISOString(),
      });
    },
    [userId]
  );

  return {
    logRequest,
    logResponse,
    logError,
  };
};

/**
 * Create a fetch wrapper with user context and error handling
 */
export const createAuthenticatedFetch = (
  getToken: () => Promise<string | null>,
  userId: string | null
) => {
  return async (
    url: string,
    options?: RequestInit
  ): Promise<Response> => {
    validateUserContext(userId);

    const token = await getToken();
    const headers = new Headers(options?.headers);

    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }

    headers.set("X-User-Id", userId || "");
    headers.set("Content-Type", "application/json");

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      if (response.status === 401) {
        // Clear auth and redirect to sign-in
        window.location.href = "/sign-in";
      }

      const error = await response.json().catch(() => ({}));
      const apiError = new Error(
        error.message || `API Error: ${response.status}`
      );
      (apiError as any).status = response.status;
      (apiError as any).response = error;

      throw apiError;
    }

    return response;
  };
};

/**
 * Hook combining all middleware and interceptors
 */
export const useAuthenticatedApi = () => {
  const { userId } = useUserContext();
  const { getToken } = useAuth();
  const { logRequest, logResponse, logError } = useRequestLogger();

  const authenticatedFetch = useCallback(
    async <T,>(
      url: string,
      options?: RequestInit
    ): Promise<T> => {
      validateUserContext(userId);

      try {
        logRequest(options?.method || "GET", url, options?.body);

        const fetch_ = createAuthenticatedFetch(getToken, userId);
        const response = await fetch_(url, options);

        const data = await response.json() as T;

        logResponse(
          options?.method || "GET",
          url,
          response.status,
          data
        );

        return data;
      } catch (error: any) {
        logError(options?.method || "GET", url, error);
        throw error;
      }
    },
    [userId, getToken, logRequest, logResponse, logError]
  );

  return {
    authenticatedFetch,
  };
};
