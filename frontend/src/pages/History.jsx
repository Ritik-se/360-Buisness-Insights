import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Clock, Trash2, FileSpreadsheet, AlertCircle } from "lucide-react";
import { listDatasets, loadDashboard, deleteDataset } from "../api/client";

export default function History({ onOpenDataset }) {
  const [datasets, setDatasets] = useState(null);
  const [error, setError] = useState(null);
  const [openingId, setOpeningId] = useState(null);
  const navigate = useNavigate();

  function refresh() {
    listDatasets().then(setDatasets).catch(() => setError("Could not load upload history."));
  }

  useEffect(() => { refresh(); }, []);

  async function handleOpen(id) {
    setOpeningId(id);
    setError(null);
    try {
      const data = await loadDashboard(id);
      onOpenDataset(data);
      navigate("/dashboard");
    } catch (err) {
      setError(err?.response?.data?.detail || "Could not open this dataset — the file may have been removed.");
    } finally {
      setOpeningId(null);
    }
  }

  async function handleDelete(id, e) {
    e.stopPropagation();
    await deleteDataset(id);
    refresh();
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-xl font-bold text-text mb-1">Upload History</h1>
      <p className="text-sm text-muted mb-6">Every dataset you've uploaded in this workspace. Click one to reopen its dashboard.</p>

      {error && (
        <div className="flex items-center gap-2 text-sm text-negative bg-card border border-border rounded-lg p-3 mb-4">
          <AlertCircle size={16} /> {error}
        </div>
      )}

      {!datasets && <p className="text-sm text-muted">Loading…</p>}

      {datasets && datasets.length === 0 && (
        <div className="bg-card border border-border rounded-lg p-8 text-center">
          <FileSpreadsheet size={28} className="mx-auto text-muted mb-2" />
          <p className="text-sm text-muted">No datasets uploaded yet.</p>
        </div>
      )}

      {datasets && datasets.length > 0 && (
        <div className="bg-card border border-border rounded-lg divide-y divide-border">
          {datasets.map((d) => (
            <div
              key={d.dataset_id}
              onClick={() => d.available && handleOpen(d.dataset_id)}
              className={`flex items-center justify-between p-4 ${d.available ? "cursor-pointer hover:bg-card-soft" : "opacity-50"}`}
            >
              <div className="flex items-center gap-3">
                <FileSpreadsheet size={18} className="text-primary shrink-0" />
                <div>
                  <div className="text-sm font-medium text-text">{d.filename}</div>
                  <div className="text-xs text-muted flex items-center gap-1 mt-0.5">
                    <Clock size={11} />
                    {new Date(d.uploaded_at).toLocaleString()} · {d.row_count.toLocaleString()} rows · {d.column_count} columns
                    {!d.available && " · file missing"}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                {openingId === d.dataset_id && <span className="text-xs text-muted">Opening…</span>}
                <button
                  onClick={(e) => handleDelete(d.dataset_id, e)}
                  title="Delete this dataset"
                  className="text-muted hover:text-negative p-1"
                >
                  <Trash2 size={15} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
