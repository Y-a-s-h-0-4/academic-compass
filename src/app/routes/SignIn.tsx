/**
 * Sign In Page
 * Handles user authentication through Clerk
 */

import React, { useEffect } from "react";
import { SignIn as ClerkSignIn } from "@clerk/clerk-react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@clerk/clerk-react";
import { Button } from "@/components/ui/button";

const SignIn: React.FC = () => {
  const { isSignedIn, isLoaded } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (isLoaded && isSignedIn) {
      navigate("/", { replace: true });
    }
  }, [isLoaded, isSignedIn, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-white px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Sign In</h1>
          <p className="text-gray-600">Welcome back to Academic Compass</p>
        </div>

        <div className="bg-white">
          <ClerkSignIn
            appearance={{
              elements: {
                rootBox: "w-full",
                card: "w-full shadow-none border-0 p-0",
                headerTitle: "hidden",
                headerSubtitle: "hidden",
                formButtonPrimary: "bg-blue-600 hover:bg-blue-700",
                footerActionLink: "text-blue-600 hover:text-blue-700",
              },
            }}
            redirectUrl="/"
            signUpUrl="/sign-up"
          />
        </div>

        <div className="mt-6 text-center text-sm text-gray-600">
          <span>Don&apos;t have an account?</span>{" "}
          <Button
            variant="link"
            className="text-blue-600 hover:text-blue-700 font-medium p-0 h-auto"
            onClick={() => navigate("/sign-up")}
          >
            Sign up
          </Button>
        </div>
      </div>
    </div>
  );
};

export default SignIn;
