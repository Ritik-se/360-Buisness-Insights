import { useEffect, useRef, useState } from "react";
import { User, Mail, Database, Camera } from "lucide-react";
import { getProfile, updateProfile, uploadAvatar, avatarUrl } from "../api/client";

export default function Profile({ dashboardData }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [avatarPath, setAvatarPath] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploadingPhoto, setUploadingPhoto] = useState(false);
  const [error, setError] = useState(null);
  const [saved, setSaved] = useState(false);
  const [signedOut, setSignedOut] = useState(false);
  const fileRef = useRef(null);

  useEffect(() => {
    getProfile()
      .then((p) => { setName(p.name); setEmail(p.email); setAvatarPath(p.avatar_url); })
      .catch(() => setSignedOut(true))
      .finally(() => setLoading(false));
  }, []);

  const initials = (name || email || "U").split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();

  async function handleSave() {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const p = await updateProfile(name);
      setName(p.name);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      setError(err?.response?.data?.detail || "Could not save changes.");
    } finally {
      setSaving(false);
    }
  }

  async function handlePhotoChange(e) {
    const file = e.target.files[0];
    if (!file) return;
    setUploadingPhoto(true);
    setError(null);
    try {
      const p = await uploadAvatar(file);
      setAvatarPath(p.avatar_url);
    } catch (err) {
      setError(err?.response?.data?.detail || "Could not upload photo.");
    } finally {
      setUploadingPhoto(false);
      e.target.value = "";
    }
  }

  if (loading) return <div className="p-8 max-w-2xl mx-auto text-sm text-muted">Loading profile…</div>;

  if (signedOut) {
    return (
      <div className="p-8 max-w-2xl mx-auto">
        <h1 className="text-xl font-bold text-text mb-1">Profile</h1>
        <p className="text-sm text-muted">Please sign in to view and edit your profile.</p>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <h1 className="text-xl font-bold text-text mb-1">Profile</h1>
      <p className="text-sm text-muted mb-6">Manage your account details.</p>

      <div className="bg-card border border-border rounded-lg p-6 mb-4">
        <div className="flex items-center gap-4 mb-6">
          <button
            onClick={() => fileRef.current?.click()}
            className="relative w-14 h-14 rounded-full bg-primary flex items-center justify-center text-white text-lg font-bold overflow-hidden group shrink-0"
            title="Change profile photo"
          >
            {avatarPath ? (
              <img src={avatarUrl(avatarPath)} alt="Profile" className="w-full h-full object-cover" />
            ) : (
              initials || "U"
            )}
            <span className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
              <Camera size={16} className="text-white" />
            </span>
          </button>
          <input ref={fileRef} type="file" accept="image/png,image/jpeg,image/webp,image/gif" className="hidden" onChange={handlePhotoChange} />
          <div>
            <div className="font-semibold text-text">{name || email}</div>
            <div className="text-sm text-muted">{email}</div>
            {uploadingPhoto && <div className="text-xs text-muted mt-0.5">Uploading photo…</div>}
          </div>
        </div>

        <label className="text-xs font-medium text-muted flex items-center gap-1.5 mb-1"><User size={12} /> Name</label>
        <input
          value={name} onChange={(e) => setName(e.target.value)}
          className="w-full mb-4 px-3 py-2 rounded-lg border border-border bg-bg text-sm outline-none focus:border-primary"
        />
        <label className="text-xs font-medium text-muted flex items-center gap-1.5 mb-1"><Mail size={12} /> Email</label>
        <input
          value={email} disabled
          className="w-full mb-4 px-3 py-2 rounded-lg border border-border bg-card-soft text-sm text-muted outline-none cursor-not-allowed"
        />

        <div className="flex items-center gap-3">
          <button
            onClick={handleSave}
            disabled={saving || !name.trim()}
            className="px-4 py-2 rounded-lg bg-primary text-white text-sm font-semibold hover:opacity-90 disabled:opacity-60"
          >
            {saving ? "Saving…" : "Save changes"}
          </button>
          {saved && <span className="text-sm text-positive">Saved</span>}
          {error && <span className="text-sm text-negative">{error}</span>}
        </div>
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
