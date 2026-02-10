/**
 * Shared TTS URL cache for LangHero.
 *
 * Caches TTS audio URLs to avoid redundant API calls.
 * Shared across all components for efficiency.
 */

import { apiFetch } from '$lib/api';
import { toBackendUrl } from './helpers';

// Global cache - persists across component mounts
const cache = new Map<string, string>();

/**
 * Build a cache key from language and text.
 */
function buildCacheKey(language: string, text: string): string {
  const lang = (language ?? '').trim().toLowerCase();
  const phrase = (text ?? '').trim();
  return `${lang}::${phrase}`;
}

/**
 * Get a cached TTS URL if available.
 */
export function getCachedTtsUrl(language: string, text: string): string | null {
  const key = buildCacheKey(language, text);
  return cache.get(key) ?? null;
}

/**
 * Set a TTS URL in the cache.
 */
export function setCachedTtsUrl(language: string, text: string, url: string): void {
  if (!url) return;
  const key = buildCacheKey(language, text);
  cache.set(key, url);
}

/**
 * Fetch TTS URL, using cache if available.
 *
 * @param text - Text to synthesize
 * @param language - Target language (e.g., "Japanese")
 * @returns Full URL to the audio file, or empty string on failure
 */
export async function fetchTtsUrl(text: string, language: string): Promise<string> {
  const phrase = (text ?? '').trim();
  if (!phrase) return '';

  // Check cache first
  const cached = getCachedTtsUrl(language, phrase);
  if (cached) return cached;

  try {
    const res = await apiFetch('/api/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: phrase, language }),
    });

    if (!res.ok) return '';

    const data = await res.json();
    const url = toBackendUrl(data?.url ?? '');

    if (url) {
      setCachedTtsUrl(language, phrase, url);
    }

    return url;
  } catch {
    return '';
  }
}

/**
 * Clear the TTS cache (useful for testing or memory management).
 */
export function clearTtsCache(): void {
  cache.clear();
}

/**
 * Get the current cache size.
 */
export function getTtsCacheSize(): number {
  return cache.size;
}
