/**
 * Language utilities for LangHero.
 *
 * Provides consistent language string normalization across the app.
 */

/**
 * Supported language codes and their canonical names.
 */
export const LANGUAGE_MAP: Record<string, string> = {
  // Japanese
  ja: 'Japanese',
  jp: 'Japanese',
  japanese: 'Japanese',

  // English
  en: 'English',
  eng: 'English',
  english: 'English',

  // Spanish
  es: 'Spanish',
  spa: 'Spanish',
  spanish: 'Spanish',
  espanol: 'Spanish',
  español: 'Spanish',
};

/**
 * Values that should be treated as "no override" / auto-detect.
 */
const AUTO_VALUES = ['auto', 'default', 'none', ''];

/**
 * Normalize a language string to its canonical form.
 *
 * @param value - Raw language input (e.g., "ja", "Japanese", "jp")
 * @returns Canonical language name (e.g., "Japanese") or empty string for auto/default
 *
 * @example
 * normalizeLanguage('ja')       // 'Japanese'
 * normalizeLanguage('JP')       // 'Japanese'
 * normalizeLanguage('japanese') // 'Japanese'
 * normalizeLanguage('auto')     // ''
 * normalizeLanguage('')         // ''
 * normalizeLanguage('Korean')   // 'Korean' (passthrough for unknown)
 */
export function normalizeLanguage(value: unknown): string {
  const raw = String(value ?? '').trim();
  if (!raw) return '';

  const lowered = raw.toLowerCase();

  // Check for auto/default values
  if (AUTO_VALUES.includes(lowered)) return '';

  // Look up in language map
  const canonical = LANGUAGE_MAP[lowered];
  if (canonical) return canonical;

  // Return as-is for unknown languages (allows extensibility)
  return raw;
}

/**
 * Check if a language string represents a valid supported language.
 */
export function isSupportedLanguage(value: unknown): boolean {
  const normalized = normalizeLanguage(value);
  return normalized !== '' && Object.values(LANGUAGE_MAP).includes(normalized);
}

/**
 * Get the list of supported languages.
 */
export function getSupportedLanguages(): string[] {
  return [...new Set(Object.values(LANGUAGE_MAP))];
}
