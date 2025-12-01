import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import { Loader2 } from "lucide-react";
import { SagilityLogo } from "@/components/SagilityLogo";
import { extractErrorMessage } from "@/utils/errorHandling";

export default function Auth() {
  const navigate = useNavigate();
  const { login, isAuthenticated, loading } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  // Redirect if already authenticated
  useEffect(() => {
    if (!loading && isAuthenticated) {
      navigate("/dashboard", { replace: true });
    }
  }, [isAuthenticated, loading, navigate]);

  const handleEntraIDLogin = async () => {
    setIsLoading(true);
    // Entra ID authentication - to be implemented
    toast.error("Entra ID authentication not yet implemented");
    setIsLoading(false);
  };


  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!email || !password) {
      toast.error("Please fill in all fields");
      return;
    }

    setIsLoading(true);
    
    try {
      await login({ email, password });
      toast.success("Successfully logged in");
      navigate("/dashboard", { replace: true });
    } catch (error: unknown) {
      const errorMessage = extractErrorMessage(error, "Login failed. Please check your credentials.");
      toast.error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center mb-4">
            <SagilityLogo className="text-foreground" width={56} height={72} />
          </div>
          <h1 className="text-2xl font-semibold text-foreground mb-2">Welcome to Sagiliti</h1>
          <p className="text-muted-foreground">Sign in to manage your utility billing</p>
        </div>

        <Card className="p-8 border border-border shadow-lg">
          {/* Entra ID Sign In */}
          <Button
            onClick={handleEntraIDLogin}
            disabled={isLoading}
            className="w-full mb-6 bg-primary hover:bg-primary-hover text-primary-foreground h-11"
          >
            <svg className="w-5 h-5 mr-2" viewBox="0 0 23 23" fill="none">
              <path
                d="M11.5 0L0 6.5V16.5L11.5 23L23 16.5V6.5L11.5 0Z"
                fill="currentColor"
              />
            </svg>
            Sign in with Entra ID
          </Button>

          {/* Divider */}
          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-4 bg-card text-muted-foreground">Or continue with email</span>
            </div>
          </div>

          {/* Email/Password Form */}
          <form onSubmit={handleEmailLogin} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email" className="text-sm font-medium text-foreground">
                Email address
              </Label>
              <Input
                id="email"
                type="email"
                placeholder="name@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="bg-background border-border"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" className="text-sm font-medium text-foreground">
                Password
              </Label>
              <Input
                id="password"
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="bg-background border-border"
                required
              />
            </div>

            <Button
              type="submit"
              disabled={isLoading}
              className="w-full bg-primary hover:bg-primary-hover text-primary-foreground h-11"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Signing in...
                </>
              ) : (
                "Sign in"
              )}
            </Button>
          </form>

          {/* Footer */}
          <div className="mt-6 text-center text-sm text-muted-foreground">
            <button className="hover:text-foreground transition-colors">
              Forgot your password?
            </button>
          </div>
        </Card>

        <p className="text-center text-sm text-muted-foreground mt-6">
          Need help?{" "}
          <button className="text-primary hover:underline">Contact support</button>
        </p>
      </div>
    </div>
  );
}
