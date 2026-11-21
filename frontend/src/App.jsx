import { useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import TopBar from "./components/TopBar";
import Login from "./pages/Login";
import UploadPage from "./pages/Upload";
import Dashboard from "./pages/Dashboard";
import Profile from "./pages/Profile";
import History from "./pages/History";
import DataPrep from "./pages/DataPrep";
import AIAnalyst from "./pages/AIAnalyst";
import Report from "./pages/Report";

function AppShell({ dashboardData, children }) {
  return (
    <div className="flex h-screen bg-bg">
      <Sidebar dashboardData={dashboardData} />
      <div className="flex-1 flex flex-col overflow-hidden">
        <TopBar />
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}

export default function App() {
  const [dashboardData, setDashboardData] = useState(null);

  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="/login" element={<Login />} />
      <Route
        path="/upload"
        element={
          <AppShell dashboardData={dashboardData}>
            <UploadPage onUploaded={setDashboardData} />
          </AppShell>
        }
      />
      <Route
        path="/dashboard"
        element={
          <AppShell dashboardData={dashboardData}>
            <Dashboard data={dashboardData} />
          </AppShell>
        }
      />
      <Route
        path="/profile"
        element={
          <AppShell dashboardData={dashboardData}>
            <Profile dashboardData={dashboardData} />
          </AppShell>
        }
      />
      <Route
        path="/history"
        element={
          <AppShell dashboardData={dashboardData}>
            <History onOpenDataset={setDashboardData} />
          </AppShell>
        }
      />
      <Route
        path="/data-prep"
        element={
          <AppShell dashboardData={dashboardData}>
            <DataPrep dashboardData={dashboardData} onCleaned={setDashboardData} />
          </AppShell>
        }
      />
      <Route
        path="/ai-analyst"
        element={
          <AppShell dashboardData={dashboardData}>
            <AIAnalyst dashboardData={dashboardData} />
          </AppShell>
        }
      />
      <Route
        path="/reports"
        element={
          <AppShell dashboardData={dashboardData}>
            <Report dashboardData={dashboardData} />
          </AppShell>
        }
      />
    </Routes>
  );
}
