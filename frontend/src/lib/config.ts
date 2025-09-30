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
