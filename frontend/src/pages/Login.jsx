import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { BarChart3 } from "lucide-react";
import { login, resendOtp, signup, verifyOtp } from "../api/client";

export default function Login() {
  const [mode, setMode] = useState("signin"); // "signin" | "signup" | "otp"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [error, setError] = useState(null);
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  function finishLogin(token, userEmail) {
    localStorage.setItem("auth_token", token);
    localStorage.setItem("auth_email", userEmail);
    navigate("/upload");
  }

  async function handleSignIn() {
    setLoading(true);
    setError(null);
    try {
      const res = await login(email, password);
      finishLogin(res.token, res.email);
    } catch (err) {
      setError(err?.response?.data?.detail || "Could not sign in.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSignUp() {
    setLoading(true);
    setError(null);
    try {
      await signup(email, password);
      setInfo(`We sent a verification code to ${email}.`);
      setMode("otp");
    } catch (err) {
      setError(err?.response?.data?.detail || "Could not create the account.");
    } finally {
      setLoading(false);
    }
  }

  async function handleVerify() {
    setLoading(true);
    setError(null);
    try {
      const res = await verifyOtp(email, otp);
      finishLogin(res.token, res.email);
    } catch (err) {
      setError(err?.response?.data?.detail || "Could not verify the code.");
    } finally {
      setLoading(false);
    }
  }

  async function handleResend() {
    setError(null);
    setInfo(null);
    try {
      await resendOtp(email);
      setInfo("A new code has been sent.");
    } catch (err) {
      setError(err?.response?.data?.detail || "Could not resend the code.");
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg p-4">
      <div className="bg-card border border-border rounded-xl p-8 w-full max-w-sm">
        <div className="flex items-center gap-2 mb-6">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-white">
            <BarChart3 size={16} />
          </div>
          <span className="font-bold text-text">Business Insights 360</span>
        </div>

        {mode !== "otp" && (
          <>
            <h1 className="text-lg font-bold text-text mb-1">{mode === "signin" ? "Welcome back" : "Create an account"}</h1>
            <p className="text-sm text-muted mb-6">
              {mode === "signin" ? "Sign in to analyze your business data" : "Sign up with your email to get started"}
            </p>

            <label className="text-xs font-medium text-muted block mb-1">Email</label>
            <input
              type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com"
              className="w-full mb-3 px-3 py-2 rounded-lg border border-border bg-card text-sm outline-none focus:border-primary"
            />
            <label className="text-xs font-medium text-muted block mb-1">Password</label>
            <input
              type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••"
              onKeyDown={(e) => e.key === "Enter" && (mode === "signin" ? handleSignIn() : handleSignUp())}
              className="w-full mb-5 px-3 py-2 rounded-lg border border-border bg-card text-sm outline-none focus:border-primary"
            />

            {error && <p className="text-sm text-negative mb-3">{error}</p>}

            <button
              onClick={mode === "signin" ? handleSignIn : handleSignUp}
              disabled={loading || !email || !password}
              className="w-full py-2.5 rounded-lg bg-primary text-white text-sm font-semibold hover:opacity-90 disabled:opacity-60"
            >
              {loading ? "Please wait…" : mode === "signin" ? "Sign in" : "Create account"}
            </button>

            <button
              onClick={() => { setMode(mode === "signin" ? "signup" : "signin"); setError(null); setInfo(null); }}
              className="w-full mt-3 text-xs text-muted hover:text-primary"
            >
              {mode === "signin" ? "Don't have an account? Create one" : "Already have an account? Sign in"}
            </button>
          </>
        )}

        {mode === "otp" && (
          <>
            <h1 className="text-lg font-bold text-text mb-1">Verify your email</h1>
            <p className="text-sm text-muted mb-6">Enter the 6-digit code we sent to {email}</p>

            <label className="text-xs font-medium text-muted block mb-1">Verification code</label>
            <input
              type="text" inputMode="numeric" maxLength={6} value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
              onKeyDown={(e) => e.key === "Enter" && handleVerify()}
              placeholder="000000"
              className="w-full mb-3 px-3 py-2 rounded-lg border border-border bg-card text-sm tracking-[0.3em] text-center outline-none focus:border-primary"
            />

            {info && <p className="text-sm text-positive mb-3">{info}</p>}
            {error && <p className="text-sm text-negative mb-3">{error}</p>}

            <button
              onClick={handleVerify}
              disabled={loading || otp.length !== 6}
              className="w-full py-2.5 rounded-lg bg-primary text-white text-sm font-semibold hover:opacity-90 disabled:opacity-60"
            >
              {loading ? "Verifying…" : "Verify & continue"}
            </button>
            <button onClick={handleResend} className="w-full mt-3 text-xs text-muted hover:text-primary">
              Resend code
            </button>
          </>
        )}
      </div>
    </div>
  );
}
