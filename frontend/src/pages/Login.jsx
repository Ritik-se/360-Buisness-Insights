import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { BarChart3 } from "lucide-react";

export default function Login() {
  const [email, setEmail] = useState("you@company.com");
  const [password, setPassword] = useState("");
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg p-4">
      <div className="bg-card border border-border rounded-xl p-8 w-full max-w-sm">
        <div className="flex items-center gap-2 mb-6">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-white">
            <BarChart3 size={16} />
          </div>
          <span className="font-bold text-text">Business Insights 360</span>
        </div>

        <h1 className="text-lg font-bold text-text mb-1">Welcome back</h1>
        <p className="text-sm text-muted mb-6">Sign in to analyze your business data</p>

        <label className="text-xs font-medium text-muted block mb-1">Email</label>
        <input
          type="text" value={email} onChange={(e) => setEmail(e.target.value)}
          className="w-full mb-3 px-3 py-2 rounded-lg border border-border bg-card text-sm outline-none focus:border-primary"
        />
        <label className="text-xs font-medium text-muted block mb-1">Password</label>
        <input
          type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••"
          className="w-full mb-5 px-3 py-2 rounded-lg border border-border bg-card text-sm outline-none focus:border-primary"
        />
        <button
          onClick={() => navigate("/upload")}
          className="w-full py-2.5 rounded-lg bg-primary text-white text-sm font-semibold hover:opacity-90"
        >
          Sign in
        </button>
      </div>
    </div>
  );
}
