import axios from "axios";

const api = axios.create({ baseURL: process.env.REACT_APP_API_URL || "http://localhost:8000" });

export const ingestDoc = (formData) =>
  api.post("/api/v1/ingest", formData, { headers: { "Content-Type": "multipart/form-data" } });

export const askQuestion = (question) =>
  api.post("/api/v1/ask", { question });

export const getStats = () => api.get("/api/v1/stats");

export const clearDocs = () => api.delete("/api/v1/documents");
