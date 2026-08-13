import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useAuth } from "@/auth/auth-context";
import { Button } from "@/components/whitfield/primitives";
import { Lock, Warehouse, AlertCircle } from "lucide-react";

export const Route = createFileRoute("/login")({
  head: () => ({
    meta: [
      { title: "Sign In — Whitfield WMS" },
      { name: "description", content: "Sign in to Whitfield Warehouse Management System." },
    ],
  }),
  component: LoginPage,
});

function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (isAuthenticated) {
    navigate({ to: "/" });
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setErrorMessage("Please enter username/email and password.");
      return;
    }

    setLoading(true);
    setErrorMessage(null);

    try {
      await login({ username: username.trim(), password });
      navigate({ to: "/" });
    } catch (err: any) {
      setErrorMessage(err.message || "Invalid credentials. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <div className="mx-auto grid size-12 place-items-center rounded-lg bg-signal">
            <Warehouse className="size-6 text-signal-foreground" />
          </div>
          <h1 className="display-lg mt-4 font-semibold tracking-tight">Whitfield Fulfillment</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Precision Warehouse Operations · Reno &amp; Columbus
          </p>
        </div>

        <div className="rounded-xl border border-border bg-surface p-6 shadow-lg sm:p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            <h2 className="text-lg font-semibold tracking-tight text-foreground">Sign in to WMS</h2>

            {errorMessage ? (
              <div className="flex items-center gap-2.5 rounded-lg border border-danger/30 bg-danger/10 px-3.5 py-3 text-xs text-danger">
                <AlertCircle className="size-4 shrink-0" />
                <span>{errorMessage}</span>
              </div>
            ) : null}

            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Username / Email
              </label>
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="admin@whitfield.com"
                className="mt-1.5 w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-signal focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Password
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="mt-1.5 w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-signal focus:outline-none"
              />
            </div>

            <Button
              type="submit"
              variant="primary"
              disabled={loading}
              className="w-full justify-center py-2.5"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <span className="size-3 animate-spin rounded-full border-2 border-signal-foreground border-t-transparent" />
                  Signing in...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <Lock className="size-4" />
                  Sign In
                </span>
              )}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
