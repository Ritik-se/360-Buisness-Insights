import { useEffect, useRef, useState } from "react";
import { Sparkle, Send, AlertCircle } from "lucide-react";
import { getAiStatus, askAi } from "../api/client";

const SUGGESTED = [
  "What are the major insights from this dataset?",
  "Which category is performing best?",
  "Which region is underperforming?",
];

export default function AIAnalyst({ dashboardData }) {
  const [configured, setConfigured] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [history, setHistory] = useState(undefined);
  const endRef = useRef(null);

  useEffect(() => { getAiStatus().then((s) => setConfigured(s.configured)); }, []);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  async function send(question) {
    if (!question.trim() || !dashboardData?.dataset_id) return;
    setMessages((m) => [...m, { role: "user", text: question }]);
    setInput("");
    setLoading(true);
    setError(null);
    try {
      const res = await askAi(dashboardData.dataset_id, question, history);
      setMessages((m) => [...m, { role: "assistant", text: res.answer }]);
      setHistory(res.history);
    } catch (err) {
      setError(err?.response?.data?.detail || "Something went wrong asking the AI Analyst.");
    } finally {
      setLoading(false);
    }
  }

  if (!dashboardData?.dataset_id) {
    return (
      <div className="p-8 max-w-2xl mx-auto">
        <h1 className="text-xl font-bold text-text mb-1">AI Business Analyst</h1>
        <p className="text-sm text-muted">Upload a dataset first to ask it questions.</p>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-3xl mx-auto flex flex-col h-full">
      <h1 className="text-xl font-bold text-text mb-1 flex items-center gap-2">
        <Sparkle size={18} className="text-primary" /> AI Business Analyst
      </h1>
      <p className="text-sm text-muted mb-4">
        Ask questions about <span className="font-medium text-text">{dashboardData.filename}</span>. Every number comes from a real calculation on your data — the AI never invents figures.
      </p>

      {configured === false && (
        <div className="flex items-start gap-2 text-sm text-muted bg-card border border-border rounded-lg p-4 mb-4">
          <AlertCircle size={16} className="mt-0.5 shrink-0" />
          <span>
            AI Analyst isn't connected yet — it needs a free <code className="text-text">GEMINI_API_KEY</code> set
            on the backend (get one at <a href="https://aistudio.google.com/apikey" target="_blank" rel="noreferrer" className="text-primary underline">aistudio.google.com/apikey</a>).
            Once that's configured and the server is restarted, this chat will work.
          </span>
        </div>
      )}

      <div className="flex-1 overflow-y-auto space-y-3 mb-4 min-h-[200px]">
        {messages.length === 0 && configured && (
          <div className="flex flex-wrap gap-2">
            {SUGGESTED.map((q) => (
              <button key={q} onClick={() => send(q)} className="text-xs px-3 py-1.5 rounded-full border border-border bg-card-soft text-text hover:bg-card">
                {q}
              </button>
            ))}
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${m.role === "user" ? "ml-auto bg-primary text-white" : "bg-card border border-border text-text"}`}>
            {m.text}
          </div>
        ))}
        {loading && <div className="text-sm text-muted">Thinking…</div>}
        {error && <div className="text-sm text-negative">{error}</div>}
        <div ref={endRef} />
      </div>

      <div className="flex items-center gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send(input)}
          placeholder={configured ? "Ask about this dataset…" : "AI Analyst not connected yet"}
          disabled={!configured}
          className="flex-1 text-sm border border-border rounded-lg px-3 py-2 bg-card text-text outline-none focus:border-primary disabled:opacity-50"
        />
        <button
          onClick={() => send(input)}
          disabled={!configured || loading}
          className="p-2.5 rounded-lg bg-primary text-white hover:opacity-90 disabled:opacity-50"
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  );
}
