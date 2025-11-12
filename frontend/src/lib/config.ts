// Centralized frontend configuration
// Backend URL helper with dev overrides via ?api=... or localStorage BACKEND_URL
let cachedUrl: string | null = null;

export function getBackendUrl(): string {
  if (cachedUrl) return cachedUrl;
  let url = 'http://localhost:8000';
  try {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const q = params.get('api');
      const ls = window.localStorage.getItem('BACKEND_URL');
      if (q) url = q;
      else if (ls) url = ls;
    }
  } catch (_) {}
  cachedUrl = url;
  return url;
}

export function setBackendUrl(url: string) {
  cachedUrl = url;
  try {
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('BACKEND_URL', url);
    }
  } catch (_) {}
}

export async function discoverBackend(candidates?: string[]): Promise<string> {
  const base = getBackendUrl();
  const uniq = new Set<string>();
  const list = candidates && candidates.length ? candidates.slice() : [];
  // Build default candidate list
  if (!list.length) {
    // Prefer 8001..8005 (dev script often picks there), then 8000
    for (let p = 8001; p <= 8005; p++) list.push(`http://localhost:${p}`);
    list.push('http://localhost:8000');
  }
  // Ensure current base is first
  list.unshift(base);
  const ordered = list.filter((u) => { if (uniq.has(u)) return false; uniq.add(u); return true; });
  for (const u of ordered) {
    try {
      const res = await fetch(`${u}/api/notes`, { method: 'GET', credentials: 'omit' });
      if (res.ok) {
        setBackendUrl(u);
        return u;
      }
    } catch (_) {
      // try next
    }
  }
  // Fall back to base
  setBackendUrl(base);
  return base;
}

export type StreamMode = "off" | "mock" | "real";

export function getStreamMode(): StreamMode {
  let mode: StreamMode = "real";
  try {
    if (typeof window === 'undefined') return mode;
    const params = new URLSearchParams(window.location.search);
    const qp = params.get('stream') ?? params.get('streamMode') ?? params.get('mockStream');
    if (qp) {
      const lowered = qp.toLowerCase();
      if (lowered === 'mock') mode = 'mock';
      else if (lowered === 'off' || lowered === '0' || lowered === 'false') mode = 'off';
      else mode = 'real';
      window.localStorage.setItem('STREAM_MODE', mode);
      return mode;
    }
    const stored = window.localStorage.getItem('STREAM_MODE');
    if (stored === 'mock' || stored === 'off' || stored === 'real') {
      mode = stored as StreamMode;
    }
  } catch (_) {
    mode = "real";
  }
  return mode;
}
