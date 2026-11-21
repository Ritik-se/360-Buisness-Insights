import { NavLink, useNavigate } from "react-router-dom";
import { LayoutGrid, Upload, BarChart3, Download, LogOut, User, Clock, Sparkles, Sparkle, FileText } from "lucide-react";
import { exportDatasetUrl } from "../api/client";

const linkClass = ({ isActive }) =>
  `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
    isActive ? "bg-primary-soft text-primary" : "text-muted hover:bg-card-soft"
  }`;

export default function Sidebar({ dashboardData }) {
  const navigate = useNavigate();
  const hasDataset = Boolean(dashboardData?.dataset_id);

  return (
    <aside className="w-56 bg-card border-r border-border flex flex-col p-4 shrink-0">
      <div className="flex items-center gap-2 mb-8 px-1">
        <div className="w-7 h-7 rounded-md bg-primary flex items-center justify-center text-white">
          <BarChart3 size={16} />
        </div>
        <span className="font-semibold text-text text-sm">Business Insights 360</span>
      </div>
      <nav className="space-y-4 flex-1 overflow-y-auto">
        <div className="space-y-1">
          <div className="px-3 text-[10px] font-semibold tracking-wide uppercase text-muted/70">Workspace</div>
          <NavLink to="/upload" className={linkClass} title="Upload a new CSV or Excel file">
            <Upload size={16} /> Upload Data
          </NavLink>
          <NavLink to="/data-prep" className={linkClass} title="Review and clean the current dataset">
            <Sparkles size={16} /> Data Preparation
          </NavLink>
        </div>

        <div className="space-y-1">
          <div className="px-3 text-[10px] font-semibold tracking-wide uppercase text-muted/70">Analyze</div>
          <NavLink to="/dashboard" className={linkClass} title="Overview, segments, trends, anomalies, forecast, what-if and data quality">
            <LayoutGrid size={16} /> Dashboard
          </NavLink>
          <NavLink to="/ai-analyst" className={linkClass} title="Ask questions about your data">
            <Sparkle size={16} /> AI Business Analyst
          </NavLink>
        </div>

        <div className="space-y-1">
          <div className="px-3 text-[10px] font-semibold tracking-wide uppercase text-muted/70">Reports</div>
          <NavLink to="/reports" className={linkClass} title="View an executive summary report">
            <FileText size={16} /> Executive Report
          </NavLink>
        </div>

        <div className="space-y-1">
          <div className="px-3 text-[10px] font-semibold tracking-wide uppercase text-muted/70">Account</div>
          <NavLink to="/profile" className={linkClass} title="View your profile">
            <User size={16} /> Profile
          </NavLink>
          <NavLink to="/history" className={linkClass} title="See and reopen past uploads">
            <Clock size={16} /> History
          </NavLink>
          {hasDataset ? (
            <a
              href={exportDatasetUrl(dashboardData.dataset_id)}
              download
              className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-muted hover:bg-card-soft transition-colors"
              title="Download the current dataset as CSV"
            >
              <Download size={16} /> Export
            </a>
          ) : (
            <div
              className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-muted/50 cursor-not-allowed"
              title="Upload a dataset first to enable export"
            >
              <Download size={16} /> Export
            </div>
          )}
        </div>
      </nav>

      <button
        onClick={() => navigate("/login")}
        className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-muted hover:bg-card-soft transition-colors"
        title="Sign out"
      >
        <LogOut size={16} /> Sign out
      </button>
    </aside>
  );
}
