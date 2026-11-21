import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FileText, UploadCloud } from "lucide-react";
import { uploadDataset } from "../api/client";

export default function UploadPage({ onUploaded }) {
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);
  const navigate = useNavigate();

  async function handleFile(file) {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const result = await uploadDataset(file);
      onUploaded(result);
      navigate("/dashboard");
    } catch (err) {
      setError(err?.response?.data?.detail || "Upload failed. Please check the file and try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <h1 className="text-xl font-bold text-text mb-1">Upload a dataset</h1>
      <p className="text-sm text-muted mb-6">
        Upload any Excel or CSV file. Columns are detected automatically — there is no fixed template.
      </p>

      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files[0]); }}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer bg-card transition-colors ${
          dragging ? "border-primary bg-primary-soft" : "border-border"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xlsx,.xls"
          className="hidden"
          onChange={(e) => handleFile(e.target.files[0])}
        />
        <div className="flex justify-center mb-3 text-muted">
          <UploadCloud size={36} strokeWidth={1.5} />
        </div>
        <div className="font-medium text-text mb-1">
          {loading ? "Analyzing dataset…" : "Drop file here or click to browse"}
        </div>
        <div className="text-sm text-muted">.xlsx or .csv, up to 25MB</div>
      </div>

      {error && (
        <div className="mt-4 text-sm text-negative bg-red-50 border border-red-200 rounded-lg p-3 flex items-center gap-2">
          <FileText size={16} /> {error}
        </div>
      )}
    </div>
  );
}
