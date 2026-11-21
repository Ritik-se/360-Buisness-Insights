import { useState } from "react";
import { User, Mail, Database } from "lucide-react";

export default function Profile({ dashboardData }) {
  const [name, setName] = useState("Your Name");
  const [email, setEmail] = useState("you@company.com");

  const initials = name.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <h1 className="text-xl font-bold text-text mb-1">Profile</h1>
      <p className="text-sm text-muted mb-6">Manage your account details.</p>

      <div className="bg-card border border-border rounded-lg p-6 mb-4">
        <div className="flex items-center gap-4 mb-6">
          <div className="w-14 h-14 rounded-full bg-primary flex items-center justify-center text-white text-lg font-bold">
            {initials || "U"}
          </div>
          <div>
            <div className="font-semibold text-text">{name}</div>
            <div className="text-sm text-muted">{email}</div>
          </div>
        </div>

        <label className="text-xs font-medium text-muted flex items-center gap-1.5 mb-1"><User size={12} /> Name</label>
        <input
          value={name} onChange={(e) => setName(e.target.value)}
          className="w-full mb-4 px-3 py-2 rounded-lg border border-border bg-bg text-sm outline-none focus:border-primary"
        />
        <label className="text-xs font-medium text-muted flex items-center gap-1.5 mb-1"><Mail size={12} /> Email</label>
        <input
          value={email} onChange={(e) => setEmail(e.target.value)}
          className="w-full mb-2 px-3 py-2 rounded-lg border border-border bg-bg text-sm outline-none focus:border-primary"
        />
        <p className="text-[11px] text-muted mt-2">
          These changes are kept only in this browser session — profile data isn't saved to an account yet.
        </p>
      </div>

      <div className="bg-card border border-border rounded-lg p-6">
        <div className="flex items-center gap-2 text-sm font-semibold text-text mb-3">
          <Database size={16} className="text-primary" /> Current session
        </div>
        {dashboardData ? (
          <div className="text-sm text-text space-y-1">
            <div>Active dataset: <span className="font-medium">{dashboardData.filename}</span></div>
            <div className="text-muted text-xs">
              {dashboardData.row_count.toLocaleString()} rows · {dashboardData.column_count} columns
            </div>
          </div>
        ) : (
          <p className="text-sm text-muted">No dataset uploaded yet this session.</p>
        )}
      </div>
    </div>
  );
}
