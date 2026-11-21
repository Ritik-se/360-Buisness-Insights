import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
});

export async function authStatus() {
  const { data } = await api.get("/api/auth/status");
  return data;
}

export async function signup(email, password) {
  const { data } = await api.post("/api/auth/signup", { email, password });
  return data;
}

export async function resendOtp(email) {
  const { data } = await api.post("/api/auth/resend-otp", { email });
  return data;
}

export async function verifyOtp(email, otp) {
  const { data } = await api.post("/api/auth/verify-otp", { email, otp });
  return data;
}

export async function login(email, password) {
  const { data } = await api.post("/api/auth/login", { email, password });
  return data;
}

export async function uploadDataset(file) {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post("/api/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function listDatasets() {
  const { data } = await api.get("/api/datasets");
  return data;
}

export async function loadDashboard(datasetId) {
  const { data } = await api.get(`/api/dashboard/${datasetId}`);
  return data;
}

export async function deleteDataset(datasetId) {
  await api.delete(`/api/datasets/${datasetId}`);
}

export async function getForecast(datasetId, periods = 3) {
  const { data } = await api.get(`/api/dashboard/${datasetId}/forecast`, { params: { periods } });
  return data;
}

export async function profileIssues(datasetId) {
  const { data } = await api.get(`/api/dataset/${datasetId}/profile-issues`);
  return data;
}

export async function previewCleaning(datasetId, operations) {
  const { data } = await api.post(`/api/dataset/${datasetId}/cleaning-preview`, operations);
  return data;
}

export async function applyCleaning(datasetId, operations) {
  const { data } = await api.post(`/api/dataset/${datasetId}/clean`, operations);
  return data;
}

export async function getChartOptions(datasetId) {
  const { data } = await api.get(`/api/dashboard/${datasetId}/chart-options`);
  return data;
}

export async function buildCustomChart(datasetId, body) {
  const { data } = await api.post(`/api/dashboard/${datasetId}/custom-chart`, body);
  return data;
}

export async function getAiStatus() {
  const { data } = await api.get("/api/ai/status");
  return data;
}

export async function askAi(datasetId, question, history) {
  const { data } = await api.post(`/api/dataset/${datasetId}/ask`, { question, history });
  return data;
}

export async function getAnomalies(datasetId) {
  const { data } = await api.get(`/api/dataset/${datasetId}/anomalies`);
  return data;
}

export async function getRootCause(datasetId, metric) {
  const { data } = await api.get(`/api/dataset/${datasetId}/root-cause`, { params: metric ? { metric } : {} });
  return data;
}

export async function simulateWhatIf(datasetId, adjustments) {
  const { data } = await api.post(`/api/dashboard/${datasetId}/simulate`, { adjustments });
  return data;
}

export async function getExecutiveReport(datasetId) {
  const { data } = await api.get(`/api/dataset/${datasetId}/report`);
  return data;
}

export function exportDatasetUrl(datasetId, filters = {}) {
  const params = new URLSearchParams(
    Object.fromEntries(Object.entries(filters).filter(([, v]) => v))
  ).toString();
  return `${api.defaults.baseURL}/api/dashboard/${datasetId}/export${params ? `?${params}` : ""}`;
}
