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
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-indigo-50 px-4">
      <div className="w-full max-w-2xl flex flex-col items-center">
        {/* Header */}
        <div className="mb-8 sm:mb-10 text-center">
          <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-2 sm:mb-3">Sign In</h1>
          <p className="text-gray-500 text-sm sm:text-base">Welcome back to Academic Compass</p>
        </div>

        {/* Auth Card */}
        <div className="bg-white rounded-xl shadow-lg border border-gray-100 overflow-hidden">
          <style>{`
              /* Global Clerk overrides */
              .cl-rootBox * {
                box-sizing: border-box !important;
              }
              
              /* Hide unwanted elements more aggressively */
              .cl-internal_ui_activity_prompt,
              .cl-rootBox [role="status"],
              .cl-userPreview,
              .cl-identityPreview,
              [data-testid="activityPrompt"],
              .cl-badge,
              .cl-headerNavigation__userPreview,
              button[aria-label*="Last"],
              .cl-signInBox ~ * {
                display: none !important;
              }
              
              /* Hide "Last used" by targeting parent and filtering */
              .cl-socialButtonsBlockButton ~ p,
              .cl-socialButtonsBlockButton ~ div,
              .cl-rootBox > [role="main"] > *:first-child::after {
                display: none !important;
              }
              
              /* Form padding and spacing */
              .cl-rootBox {
                padding: 2rem !important;
                margin: 0 !important;
                width: 100% !important;
              }
              
              .cl-formContainer {
                padding: 0 !important;
                margin: 0 !important;
              }
              
              .cl-form__innerSection {
                margin: 0 !important;
              }
              
              /* Form Fields */
              .cl-formField {
                margin-bottom: 1.5rem !important;
                padding: 0 !important;
              }
              
              .cl-formField:last-child {
                margin-bottom: 0 !important;
              }
              
              /* Inputs */
              .cl-formField input,
              .cl-input,
              input[type="email"],
              input[type="password"],
              input[type="text"] {
                width: 100% !important;
                padding: 0.625rem 1rem !important;
                border: 1px solid #d1d5db !important;
                border-radius: 0.5rem !important;
                font-size: 0.875rem !important;
                min-height: 2.5rem !important;
                transition: all 0.2s !important;
                background-color: #fff !important;
                box-sizing: border-box !important;
              }
              
              input::placeholder {
                color: #9ca3af !important;
              }
              
              input:focus {
                outline: none !important;
                border-color: #2563eb !important;
                box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.1) !important;
              }
              
              /* Labels */
              .cl-formField label,
              .cl-labelBase {
                font-weight: 500 !important;
                font-size: 0.875rem !important;
                margin-bottom: 0.5rem !important;
                color: #374151 !important;
                display: block !important;
              }
              
              /* Buttons */
              .cl-button,
              button[type="submit"],
              .cl-formButtonPrimary {
                width: 100% !important;
                padding: 0.625rem 1rem !important;
                min-height: 2.5rem !important;
                border-radius: 0.5rem !important;
                font-weight: 600 !important;
                margin: 1rem 0 0 0 !important;
                border: none !important;
                cursor: pointer !important;
                transition: all 0.2s !important;
              }
              
              .cl-button:hover,
              button[type="submit"]:hover {
                opacity: 0.9 !important;
              }
              
              /* Social Buttons */
              .cl-socialButtons {
                display: flex !important;
                flex-direction: column !important;
                gap: 0.75rem !important;
                margin-bottom: 1.5rem !important;
              }
              
              .cl-socialButtonsBlockButton,
              button[aria-label*="Google"],
              button[aria-label*="Facebook"] {
                width: 100% !important;
                padding: 0.625rem 1rem !important;
                margin: 0 !important;
                border: 1px solid #d1d5db !important;
                border-radius: 0.5rem !important;
                min-height: 2.5rem !important;
                background: #fff !important;
                color: #374151 !important;
                font-weight: 500 !important;
                font-size: 0.875rem !important;
                cursor: pointer !important;
                transition: all 0.2s !important;
              }
              
              .cl-socialButtonsBlockButton:hover {
                background: #f9fafb !important;
              }
              
              /* Divider */
              .cl-dividerRow {
                margin: 1.5rem 0 !important;
                display: flex !important;
                align-items: center !important;
              }
              
              .cl-divider {
                flex: 1 !important;
                border-top: 1px solid #d1d5db !important;
              }
              
              .cl-dividerText {
                padding: 0 1rem !important;
                font-size: 0.75rem !important;
                color: #6b7280 !important;
              }
          `}</style>
          
          <ClerkSignIn
            appearance={{
              layout: "optimized",
              variables: {
                colorPrimary: "#2563eb",
                colorInputBackground: "#ffffff",
                colorInputBorder: "#d1d5db",
                borderRadius: "0.5rem",
              },
              elements: {
                headerTitle: "hidden",
                headerSubtitle: "hidden",
                header: "hidden",
                footer: "hidden",
                identityPreview: "hidden",
              },
            }}
            redirectUrl="/"
            signUpUrl="/sign-up"
          />
        </div>

        {/* Sign Up Link */}
        <div className="mt-8 text-center text-sm">
          <span className="text-gray-600">Don&apos;t have an account?</span>{" "}
          <Button
            variant="link"
            className="text-blue-600 hover:text-blue-700 font-semibold p-0 h-auto underline-offset-2 hover:underline"
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
