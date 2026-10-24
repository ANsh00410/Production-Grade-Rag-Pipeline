// In Docker: Nginx proxies /api/* → backend:8000, so BASE_URL = "/api"
// In dev:    Vite dev server talks directly to localhost:8000
const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function checkHealth() {
  const res = await fetch(`${BASE_URL}/health`);
  if (!res.ok) throw new Error("Backend offline");
  return res.json();
}

export async function queryPipeline(question) {
  const res = await fetch(`${BASE_URL}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Query failed");
  }
  return res.json();
}

export async function ingestFile(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE_URL}/ingest`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Ingest failed");
  }
  return res.json();
}

export async function getCollections() {
  const res = await fetch(`${BASE_URL}/collections`);
  if (!res.ok) throw new Error("Could not fetch collections");
  return res.json();
}
