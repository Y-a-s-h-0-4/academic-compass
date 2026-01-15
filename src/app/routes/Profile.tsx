import React, { useState } from "react";
import { useUserContext } from "@/context/UserContext";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  ArrowLeft,
  Mail,
  User,
  Phone,
  MapPin,
  LogOut,
  Edit2,
  Save,
  X,
} from "lucide-react";

const Profile: React.FC = () => {
  const navigate = useNavigate();
  const { userId, email, firstName, lastName, profileImage, logout } =
    useUserContext();
  const [isEditing, setIsEditing] = useState(false);
  const [showLogoutDialog, setShowLogoutDialog] = useState(false);
  const [formData, setFormData] = useState({
    firstName: firstName || "",
    lastName: lastName || "",
    email: email || "",
    phone: "",
    location: "",
  });

  const initials = `${firstName?.[0] || ""}${lastName?.[0] || ""}`.toUpperCase();

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSave = () => {
    // TODO: Implement save to backend
    console.log("Saving profile:", formData);
    setIsEditing(false);
  };

  const handleLogout = async () => {
    await logout();
    navigate("/sign-in", { replace: true });
  };

  const handleCancel = () => {
    setFormData({
      firstName: firstName || "",
      lastName: lastName || "",
      email: email || "",
      phone: "",
      location: "",
    });
    setIsEditing(false);
  };

  return (
    <div className="min-h-screen bg-background flex">
      {/* Ambient glow effect */}
      <div 
        className="fixed inset-0 pointer-events-none bg-[radial-gradient(ellipse_at_top_left,hsl(38,92%,50%,0.08),transparent_50%),radial-gradient(ellipse_at_bottom_right,hsl(38,60%,35%,0.05),transparent_50%)]"
      />

      <div className="w-full relative">
        <div className="max-w-4xl mx-auto p-8">
          {/* Header */}
          <div className="flex items-center justify-between mb-8">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => navigate("/")}
                className="hover:bg-primary/10"
              >
                <ArrowLeft className="h-5 w-5" />
              </Button>
              <h1 className="font-serif text-3xl text-foreground">My Profile</h1>
            </div>

            <div className="flex gap-2">
              {isEditing ? (
                <>
                  <Button
                    onClick={handleCancel}
                    variant="outline"
                    className="gap-2"
                  >
                    <X className="h-4 w-4" />
                    Cancel
                  </Button>
                  <Button onClick={handleSave} className="gap-2">
                    <Save className="h-4 w-4" />
                    Save Changes
                  </Button>
                </>
              ) : (
                <Button
                  onClick={() => setIsEditing(true)}
                  className="gap-2"
                >
                  <Edit2 className="h-4 w-4" />
                  Edit Profile
                </Button>
              )}
            </div>
          </div>

          {/* Profile Content */}
          <div className="grid gap-6">
            {/* Profile Card */}
            <Card className="p-8 bg-card/50 backdrop-blur border-border">
              <div className="flex flex-col gap-8">
                {/* Avatar Section */}
                <div className="flex items-start gap-6">
                  <Avatar className="h-24 w-24 border-4 border-primary/20">
                    {profileImage && (
                      <AvatarImage src={profileImage} alt="Profile" />
                    )}
                    <AvatarFallback className="text-lg font-semibold bg-primary text-primary-foreground">
                      {initials}
                    </AvatarFallback>
                  </Avatar>

                  <div className="flex-1">
                    <h2 className="font-serif text-2xl text-foreground mb-2">
                      {firstName} {lastName}
                    </h2>
                    <p className="text-muted-foreground mb-4">{email}</p>
                    <div className="flex gap-2">
                      <span className="px-3 py-1 bg-primary/10 text-primary rounded-full text-sm font-medium">
                        Free Plan
                      </span>
                      <span className="px-3 py-1 bg-green-500/10 text-green-600 dark:text-green-400 rounded-full text-sm font-medium">
                        Active
                      </span>
                    </div>
                  </div>
                </div>

                {/* Divider */}
                <div className="border-t border-border"></div>

                {/* Profile Information */}
                <Tabs defaultValue="about" className="w-full">
                  <TabsList className="grid w-full grid-cols-3 bg-muted">
                    <TabsTrigger value="about">About</TabsTrigger>
                    <TabsTrigger value="activity">Activity</TabsTrigger>
                    <TabsTrigger value="settings">Settings</TabsTrigger>
                  </TabsList>

                  <TabsContent value="about" className="space-y-6 mt-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      {/* First Name */}
                      <div>
                        <Label className="text-sm font-semibold text-foreground mb-2 flex items-center gap-2">
                          <User className="h-4 w-4" />
                          First Name
                        </Label>
                        {isEditing ? (
                          <Input
                            name="firstName"
                            value={formData.firstName}
                            onChange={handleInputChange}
                            className="mt-2"
                          />
                        ) : (
                          <p className="text-foreground font-medium mt-2">
                            {formData.firstName || "-"}
                          </p>
                        )}
                      </div>

                      {/* Last Name */}
                      <div>
                        <Label className="text-sm font-semibold text-foreground mb-2 flex items-center gap-2">
                          <User className="h-4 w-4" />
                          Last Name
                        </Label>
                        {isEditing ? (
                          <Input
                            name="lastName"
                            value={formData.lastName}
                            onChange={handleInputChange}
                            className="mt-2"
                          />
                        ) : (
                          <p className="text-foreground font-medium mt-2">
                            {formData.lastName || "-"}
                          </p>
                        )}
                      </div>

                      {/* Email */}
                      <div>
                        <Label className="text-sm font-semibold text-foreground mb-2 flex items-center gap-2">
                          <Mail className="h-4 w-4" />
                          Email
                        </Label>
                        <p className="text-foreground font-medium mt-2">
                          {formData.email}
                        </p>
                      </div>

                      {/* Phone */}
                      <div>
                        <Label className="text-sm font-semibold text-foreground mb-2 flex items-center gap-2">
                          <Phone className="h-4 w-4" />
                          Phone
                        </Label>
                        {isEditing ? (
                          <Input
                            name="phone"
                            value={formData.phone}
                            onChange={handleInputChange}
                            placeholder="Add phone number"
                            className="mt-2"
                          />
                        ) : (
                          <p className="text-foreground font-medium mt-2">
                            {formData.phone || "-"}
                          </p>
                        )}
                      </div>

                      {/* Location */}
                      <div className="md:col-span-2">
                        <Label className="text-sm font-semibold text-foreground mb-2 flex items-center gap-2">
                          <MapPin className="h-4 w-4" />
                          Location
                        </Label>
                        {isEditing ? (
                          <Input
                            name="location"
                            value={formData.location}
                            onChange={handleInputChange}
                            placeholder="Add your location"
                            className="mt-2"
                          />
                        ) : (
                          <p className="text-foreground font-medium mt-2">
                            {formData.location || "-"}
                          </p>
                        )}
                      </div>

                      {/* User ID */}
                      <div className="md:col-span-2">
                        <Label className="text-sm font-semibold text-foreground">
                          User ID
                        </Label>
                        <p className="text-muted-foreground text-sm mt-2 font-mono bg-muted p-3 rounded-lg border border-border">
                          {userId}
                        </p>
                      </div>
                    </div>
                  </TabsContent>

                  <TabsContent value="activity" className="space-y-6 mt-6">
                    <div className="bg-muted/50 rounded-lg p-6 border border-border">
                      <h3 className="font-semibold text-foreground mb-4">
                        Learning Statistics
                      </h3>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="bg-card rounded-lg p-4 text-center border border-border">
                          <p className="text-3xl font-bold text-primary">0</p>
                          <p className="text-sm text-muted-foreground mt-2">
                            Courses Completed
                          </p>
                        </div>
                        <div className="bg-card rounded-lg p-4 text-center border border-border">
                          <p className="text-3xl font-bold text-green-600 dark:text-green-400">0</p>
                          <p className="text-sm text-muted-foreground mt-2">
                            Learning Hours
                          </p>
                        </div>
                        <div className="bg-card rounded-lg p-4 text-center border border-border">
                          <p className="text-3xl font-bold text-purple-600 dark:text-purple-400">0</p>
                          <p className="text-sm text-muted-foreground mt-2">
                            Quiz Attempts
                          </p>
                        </div>
                        <div className="bg-card rounded-lg p-4 text-center border border-border">
                          <p className="text-3xl font-bold text-primary">0</p>
                          <p className="text-sm text-muted-foreground mt-2">
                            Resources Saved
                          </p>
                        </div>
                      </div>
                    </div>

                    <div className="bg-muted/50 rounded-lg p-6 border border-border">
                      <h3 className="font-semibold text-foreground mb-4">
                        Recent Activity
                      </h3>
                      <p className="text-muted-foreground text-center py-8">
                        No recent activity yet. Start learning to see your
                        progress here!
                      </p>
                    </div>
                  </TabsContent>

                  <TabsContent value="settings" className="space-y-6 mt-6">
                    <div className="space-y-4">
                      <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg border border-border">
                        <div>
                          <p className="font-semibold text-foreground">
                            Email Notifications
                          </p>
                          <p className="text-sm text-muted-foreground">
                            Receive updates about your learning progress
                          </p>
                        </div>
                        <Button variant="outline">Manage</Button>
                      </div>

                      <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg border border-border">
                        <div>
                          <p className="font-semibold text-foreground">
                            Data & Privacy
                          </p>
                          <p className="text-sm text-muted-foreground">
                            Control how your data is used
                          </p>
                        </div>
                        <Button variant="outline">Manage</Button>
                      </div>

                      <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg border border-border">
                        <div>
                          <p className="font-semibold text-foreground">
                            Connected Accounts
                          </p>
                          <p className="text-sm text-muted-foreground">
                            Manage your connected social accounts
                          </p>
                        </div>
                        <Button variant="outline">Manage</Button>
                      </div>
                    </div>

                    <div className="border-t border-border pt-6">
                      <Button
                        onClick={() => setShowLogoutDialog(true)}
                        variant="destructive"
                        className="w-full gap-2"
                      >
                        <LogOut className="h-4 w-4" />
                        Sign Out
                      </Button>
                    </div>
                  </TabsContent>
                </Tabs>
              </div>
            </Card>
          </div>
        </div>
      </div>

      {/* Logout Confirmation Dialog */}
      <AlertDialog open={showLogoutDialog} onOpenChange={setShowLogoutDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Sign Out?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to sign out of your account? You'll need to
              sign back in to access your learning materials.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="flex gap-3 justify-end">
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleLogout}
              className="bg-red-600 hover:bg-red-700"
            >
              Sign Out
            </AlertDialogAction>
          </div>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default Profile;
