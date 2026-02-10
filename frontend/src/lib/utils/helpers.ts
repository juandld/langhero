/**
 * General helper utilities for LangHero.
 */

import { getBackendUrl } from '$lib/config';

/**
 * Clamp a value between 0 and 1.
 */
export function clamp01(value: unknown): number {
  const num = Number(value);
  if (!Number.isFinite(num)) return 0;
  return Math.min(1, Math.max(0, num));
}

/**
 * Clamp a value between min and max.
 */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

/**
 * Convert a relative path or URL to a full backend URL.
 *
 * @param pathOrUrl - Relative path (e.g., "/api/tts") or full URL
 * @returns Full URL with backend base
 *
 * @example
 * toBackendUrl('/api/tts')           // 'http://localhost:8000/api/tts'
 * toBackendUrl('https://example.com') // 'https://example.com' (unchanged)
 * toBackendUrl('api/tts')            // 'http://localhost:8000/api/tts'
 */
export function toBackendUrl(pathOrUrl: string | null | undefined): string {
  const raw = String(pathOrUrl ?? '').trim();
  if (!raw) return '';

  // Already a full URL
  if (/^https?:\/\//.test(raw)) return raw;

  const backend = getBackendUrl().replace(/\/$/, '');
  const normalized = raw.startsWith('/') ? raw : `/${raw}`;
  return `${backend}${normalized}`;
}

/**
 * Debounce a function call.
 */
export function debounce<T extends (...args: unknown[]) => unknown>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout>;
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), delay);
  };
}

/**
 * Safe JSON parse with fallback.
 */
export function safeJsonParse<T>(json: string, fallback: T): T {
  try {
    return JSON.parse(json) as T;
  } catch {
    return fallback;
  }
}

/**
 * Generate a simple unique ID.
 */
export function generateId(): string {
  return Math.random().toString(36).substring(2, 11);
}
