import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { OnboardingLayout } from "@/components/OnboardingLayout";
import { FormField } from "@/components/FormField";
import { Button } from "@/components/ui/button";
import { api, apiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { nextOnboardingRoute } from "@/lib/onboarding";

export default function Login() {
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const [form, setForm] = useState({ email: "", password: "" });
  const [serverError, setServerError] = useState("");
  const [loading, setLoading] = useState(false);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (ev) => {
    ev.preventDefault();
    setServerError("");
    setLoading(true);
    try {
      const { data } = await api.post("/auth/login", form);
      setUser(data);
      navigate(nextOnboardingRoute(data));
    } catch (err) {
      setServerError(apiError(err.response?.data?.detail) || "Could not sign you in.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <OnboardingLayout back="/">
      <div className="mx-auto max-w-md">
        <h1 className="font-display text-3xl font-normal tracking-tight text-foreground">Welcome back</h1>
        <p className="mt-2 text-sm text-muted-foreground">Sign in to continue your health intelligence.</p>

        <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
          <FormField id="email" label="Email" type="email" value={form.email} onChange={set("email")}
            autoComplete="email" required testid="login-email" />
          <FormField id="password" label="Password" type="password" value={form.password} onChange={set("password")}
            autoComplete="current-password" required testid="login-password" />

          {serverError && (
            <p role="alert" className="rounded-xl bg-error/10 px-4 py-3 text-sm font-medium text-error" data-testid="login-error">
              {serverError}
            </p>
          )}

          <Button type="submit" disabled={loading} data-testid="login-submit"
            className="mt-2 h-12 rounded-full bg-primary text-primary-foreground hover:opacity-90">
            {loading ? "Signing in…" : "Sign in"}
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-muted-foreground">
          New to Dumosense?{" "}
          <Link to="/start" className="font-medium text-primary hover:underline" data-testid="login-to-register">
            Create an account
          </Link>
        </p>
      </div>
    </OnboardingLayout>
  );
}
