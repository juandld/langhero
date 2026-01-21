// Centralized frontend configuration
// Priority (from highest → lowest):
// - PUBLIC_BACKEND_URL (runtime env)
// - Query param ?api=...
// - localStorage BACKEND_URL
// - Compute from window.location (same-origin for non-localhost; http://localhost:8000 for localhost)

import { env as publicEnv } from '$env/dynamic/public';

function computeRuntimeBackend(): string {
  try {
    if (typeof window !== 'undefined' && window.location) {
      const { protocol, hostname } = window.location;
      if (hostname === 'localhost' || hostname === '127.0.0.1') {
        return 'http://localhost:8000';
      }
      // For tunneled/public access, assume same-origin reverse proxy in prod.
      return `${protocol}//${hostname}`;
    }
  } catch {}
  return 'http://localhost:8000';
}

let cachedUrl: string | null = null;

export function getBackendUrl(): string {
  if (cachedUrl) return cachedUrl;
  const envUrl = (publicEnv?.PUBLIC_BACKEND_URL || '').trim();
  if (envUrl) {
    cachedUrl = envUrl;
    return envUrl;
  }
  let override: string | null = null;
  try {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const q = params.get('api');
      const ls = window.localStorage.getItem('BACKEND_URL');
      override = q || ls;
    }
  } catch {}
  cachedUrl = (override && override.trim()) || computeRuntimeBackend();
  return cachedUrl;
}

export function setBackendUrl(url: string) {
  cachedUrl = url;
  try {
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('BACKEND_URL', url);
    }
  } catch {}
}

export async function discoverBackend(candidates?: string[]): Promise<string> {
  const base = getBackendUrl();
  const uniq = new Set<string>();
  const list = candidates && candidates.length ? candidates.slice() : [];
  // Build default candidate list (local-only; avoids self-probing public tunnels)
  if (!list.length) {
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
    } catch {
      // try next
    }
  }
  setBackendUrl(base);
  return base;
}

export type StreamMode = 'off' | 'mock' | 'real';

export function getStreamMode(): StreamMode {
  let mode: StreamMode = 'real';
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
  } catch {
    mode = 'real';
  }
  return mode;
}
