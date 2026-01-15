/**
 * User Context Provider
 * Provides user data and authentication state throughout the app
 */

import React, { createContext, useContext, useEffect, useState } from "react";
import { useAuth, useUser } from "@clerk/clerk-react";

export interface UserContextType {
  userId: string | null;
  email: string | null;
  firstName: string | null;
  lastName: string | null;
  fullName: string | null;
  profileImage: string | null;
  isSignedIn: boolean;
  isLoading: boolean;
  user: any;
  logout: () => Promise<void>;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

export const UserProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const { isLoaded, isSignedIn, signOut } = useAuth();
  const { user, isLoaded: userIsLoaded } = useUser();
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Set loading to false once Clerk is loaded
    if (isLoaded && userIsLoaded) {
      setIsLoading(false);
    }
  }, [isLoaded, userIsLoaded]);

  const handleLogout = async () => {
    try {
      await signOut();
    } catch (error) {
      console.error("Error signing out:", error);
    }
  };

  const value: UserContextType = {
    userId: user?.id || null,
    email: user?.emailAddresses?.[0]?.emailAddress || null,
    firstName: user?.firstName || null,
    lastName: user?.lastName || null,
    fullName: user?.fullName || null,
    profileImage: user?.profileImageUrl || null,
    isSignedIn: isSignedIn || false,
    isLoading,
    user,
    logout: handleLogout,
  };

  return (
    <UserContext.Provider value={value}>{children}</UserContext.Provider>
  );
};

/**
 * Hook to use User Context
 * @returns UserContextType
 */
export const useUserContext = (): UserContextType => {
  const context = useContext(UserContext);
  if (!context) {
    throw new Error("useUserContext must be used within UserProvider");
  }
  return context;
};
