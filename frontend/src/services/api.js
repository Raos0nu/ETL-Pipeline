/**
 * DataFlow Studio — Centralised API Service Layer
 * ─────────────────────────────────────────────────
 * All HTTP calls go through this module.
 * Features:
 *   • Axios instance with base URL + timeout
 *   • Request/response interceptors (logging, error normalisation)
 *   • Automatic retry with exponential backoff (non-5xx excluded)
 *   • Typed helper methods for every endpoint
 */

import axios from "axios";

// ── Axios instance ────────────────────────────────────────────────────────────
// Always use relative URLs — in dev the React proxy (package.json "proxy" field)
// forwards /api/* to Flask on port 5000. In production Flask serves everything.
const BASE_URL = "";

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30_000,
  headers: { "Content-Type": "application/json" },
});

// ── Retry helper ──────────────────────────────────────────────────────────────
const MAX_RETRIES = 2;
const RETRY_DELAY = 800; // ms base

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const config = error.config || {};
    config._retryCount = config._retryCount || 0;

    const shouldRetry =
      config._retryCount < MAX_RETRIES &&
      error.response?.status >= 500 &&
      config.method?.toLowerCase() === "get"; // only retry GETs

    if (shouldRetry) {
      config._retryCount += 1;
      const delay = RETRY_DELAY * 2 ** (config._retryCount - 1);
      console.warn(
        `[API] Retry ${config._retryCount}/${MAX_RETRIES} for ${config.url} in ${delay}ms`
      );
      await sleep(delay);
      return api(config);
    }

    return Promise.reject(_normaliseError(error));
  }
);

// ── Request interceptor — attach request ID ────────────────────────────────
api.interceptors.request.use((config) => {
  config.headers["X-Request-ID"] = Math.random().toString(36).slice(2, 10);
  return config;
});

// ── Error normalisation ───────────────────────────────────────────────────────
function _normaliseError(error) {
  if (error.response) {
    const msg =
      error.response.data?.error ||
      error.response.data?.message ||
      `Request failed with status ${error.response.status}`;
    const normalised = new Error(msg);
    normalised.status = error.response.status;
    normalised.data   = error.response.data;
    return normalised;
  }
  if (error.request) {
    return new Error(
      "No response from server. Check your connection or try again."
    );
  }
  return error;
}

// ═════════════════════════════════════════════════════════════════════════════
// API METHODS
// ═════════════════════════════════════════════════════════════════════════════

// ── Health & Status ────────────────────────────────────────────────────────────
export const getHealth  = () => api.get("/api/health");
export const getStatus  = () => api.get("/api/status");

// ── Data CRUD ─────────────────────────────────────────────────────────────────
export const getData = (params = {}) =>
  api.get("/api/data", { params });

export const getRecord = (orderId) =>
  api.get(`/api/data/${orderId}`);

export const createRecord = (payload) =>
  api.post("/api/data", payload);

export const updateRecord = (orderId, payload) =>
  api.put(`/api/data/${orderId}`, payload);

export const deleteRecord = (orderId) =>
  api.delete(`/api/data/${orderId}`);

export const bulkDeleteRecords = (orderIds) =>
  api.post("/api/data/bulk-delete", { order_ids: orderIds });

export const importCSV = (file, onUploadProgress) => {
  const form = new FormData();
  form.append("file", file);
  return api.post("/api/data/import", form, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress,
    timeout: 120_000, // larger timeout for big files
  });
};

export const exportCSV = () => {
  window.open(`${BASE_URL}/api/data/export`, "_blank");
};

// ── Analytics ─────────────────────────────────────────────────────────────────
export const getAnalyticsOverview   = () => api.get("/api/analytics/overview");
export const getProductAnalytics    = () => api.get("/api/analytics/products");
export const getTimeseriesAnalytics = () => api.get("/api/analytics/timeseries");
export const getAnalyticsSummary    = (top = 5) =>
  api.get("/api/analytics/summary", { params: { top } });

// ── ETL Pipeline ──────────────────────────────────────────────────────────────
export const runETL = (mode = "sync", triggeredBy = "dashboard") =>
  api.post("/api/etl/run", { mode, triggered_by: triggeredBy });

export const getJobStatus  = (jobId) => api.get(`/api/etl/status/${jobId}`);
export const getJobHistory = (limit = 20) =>
  api.get("/api/etl/history", { params: { limit } });

export default api;
