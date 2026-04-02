const normalizeBase = (value) => (value ? value.replace(/\/$/, "") : "");

export const API_BASE_URL = normalizeBase(import.meta.env.VITE_API_BASE_URL || "");

const protocol = window.location.protocol === "https:" ? "wss" : "ws";
const defaultWsBase = `${protocol}://${window.location.host}`;
export const WS_BASE_URL = normalizeBase(
  import.meta.env.VITE_WS_BASE_URL || defaultWsBase
);

export const apiUrl = (path) => `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
export const wsUrl = (path = "/ws/stream") => `${WS_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
