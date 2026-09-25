import { useState } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";
import { OnboardingLayout } from "@/components/OnboardingLayout";
import { FormField } from "@/components/FormField";
import { Button } from "@/components/ui/button";
import { api, apiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

export default function Register() {
  const navigate = useNavigate();
  const location = useLocation();
  const { setUser } = useAuth();
  const startingPoint = location.state?.starting_point;

  const [form, setForm] = useState({ first_name: "", last_name: "", email: "", password: "" });
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState("");
  const [loading, setLoading] = useState(false);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const validate = () => {
    const e = {};
    if (!form.first_name.trim()) e.first_name = "Please enter your first name.";
    if (!form.last_name.trim()) e.last_name = "Please enter your last name.";
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) e.email = "Please enter a valid email address.";
    if (form.password.length < 8) e.password = "Use at least 8 characters.";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const submit = async (ev) => {
    ev.preventDefault();
    setServerError("");
    if (!validate()) return;
    setLoading(true);
    try {
      const { data } = await api.post("/auth/register", form);
      setUser(data);
      if (startingPoint) {
        await api.put("/onboarding", { starting_point: startingPoint });
      }
      navigate("/privacy-promise");
    } catch (err) {
      setServerError(apiError(err.response?.data?.detail) || "Could not create your account.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <OnboardingLayout back="/start">
      <div className="mx-auto max-w-md">
        <h1 className="font-display text-3xl font-normal tracking-tight text-foreground">Create your account</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          A few basics to begin. You can add more later — nothing sensitive is needed now.
        </p>

        <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
          <div className="grid grid-cols-2 gap-3">
            <FormField id="first_name" label="First name" value={form.first_name} onChange={set("first_name")}
              error={errors.first_name} autoComplete="given-name" required testid="register-first-name" />
            <FormField id="last_name" label="Last name" value={form.last_name} onChange={set("last_name")}
              error={errors.last_name} autoComplete="family-name" required testid="register-last-name" />
          </div>
          <FormField id="email" label="Email" type="email" value={form.email} onChange={set("email")}
            error={errors.email} autoComplete="email" required testid="register-email" />
          <FormField id="password" label="Password" type="password" value={form.password} onChange={set("password")}
            error={errors.password} helper="At least 8 characters." autoComplete="new-password" required testid="register-password" />

          {serverError && (
            <p role="alert" className="rounded-xl bg-error/10 px-4 py-3 text-sm font-medium text-error" data-testid="register-error">
              {serverError}
            </p>
          )}

          <Button type="submit" disabled={loading} data-testid="register-submit"
            className="mt-2 h-12 rounded-full bg-primary text-primary-foreground hover:opacity-90">
            {loading ? "Creating…" : "Create account"}
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-primary hover:underline" data-testid="register-to-login">
            Sign in
          </Link>
        </p>
      </div>
    </OnboardingLayout>
  );
}
