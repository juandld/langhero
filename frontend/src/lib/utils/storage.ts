/**
 * localStorage utilities for LangHero.
 *
 * Provides type-safe storage with error handling and SSR safety.
 */

import { browser } from '$app/environment';

/**
 * Storage keys used throughout the app.
 * Centralized here to avoid magic strings and collisions.
 */
export const STORAGE_KEYS = {
  // Audio settings
  VOLUME: 'LANGHERO_VOLUME_V1',
  VOLUME_PREV: 'LANGHERO_VOLUME_V1_prev',
  SPEED: 'LANGHERO_SPEED_V1',
  AUTO_NARRATE: 'LANGHERO_AUTO_NARRATE_V1',

  // Device settings
  MIC_DEVICE_ID: 'LANGHERO_MIC_DEVICE_ID_V1',

  // Game settings
  JUDGE_FOCUS: 'JUDGE_FOCUS',
  LANGUAGE_OVERRIDE: 'LANGUAGE_OVERRIDE',

  // Profile & progress
  PROFILE: 'LANGHERO_PROFILE_V1',
  RUNS: 'langhero_runs_v2',
  ACTIVE_RUN: 'langhero_active_run',
  STORY_PROGRESS: 'LANGHERO_STORY_PROGRESS_V1',
} as const;

export type StorageKey = (typeof STORAGE_KEYS)[keyof typeof STORAGE_KEYS];

/**
 * Safely get a string value from localStorage.
 *
 * @param key - Storage key
 * @param fallback - Default value if not found or on error
 * @returns The stored value or fallback
 */
export function getString(key: string, fallback = ''): string {
  if (!browser) return fallback;
  try {
    return localStorage.getItem(key) ?? fallback;
  } catch {
    return fallback;
  }
}

/**
 * Safely set a string value in localStorage.
 *
 * @param key - Storage key
 * @param value - Value to store
 * @returns true if successful, false on error
 */
export function setString(key: string, value: string): boolean {
  if (!browser) return false;
  try {
    localStorage.setItem(key, value);
    return true;
  } catch {
    return false;
  }
}

/**
 * Safely remove a key from localStorage.
 *
 * @param key - Storage key
 * @returns true if successful, false on error
 */
export function remove(key: string): boolean {
  if (!browser) return false;
  try {
    localStorage.removeItem(key);
    return true;
  } catch {
    return false;
  }
}

/**
 * Safely get a number from localStorage.
 *
 * @param key - Storage key
 * @param fallback - Default value if not found, invalid, or on error
 * @param min - Optional minimum value
 * @param max - Optional maximum value
 */
export function getNumber(
  key: string,
  fallback: number,
  min?: number,
  max?: number
): number {
  const str = getString(key, '');
  if (!str) return fallback;

  const num = parseFloat(str);
  if (!Number.isFinite(num)) return fallback;

  let result = num;
  if (min !== undefined) result = Math.max(min, result);
  if (max !== undefined) result = Math.min(max, result);

  return result;
}

/**
 * Safely set a number in localStorage.
 */
export function setNumber(key: string, value: number): boolean {
  return setString(key, String(value));
}

/**
 * Safely get a boolean from localStorage.
 */
export function getBoolean(key: string, fallback: boolean): boolean {
  const str = getString(key, '');
  if (!str) return fallback;
  return str === 'true';
}

/**
 * Safely set a boolean in localStorage.
 */
export function setBoolean(key: string, value: boolean): boolean {
  return setString(key, String(value));
}

/**
 * Safely get and parse JSON from localStorage.
 *
 * @param key - Storage key
 * @param fallback - Default value if not found, invalid JSON, or on error
 */
export function getJson<T>(key: string, fallback: T): T {
  const str = getString(key, '');
  if (!str) return fallback;

  try {
    return JSON.parse(str) as T;
  } catch {
    return fallback;
  }
}

/**
 * Safely stringify and store JSON in localStorage.
 */
export function setJson<T>(key: string, value: T): boolean {
  try {
    return setString(key, JSON.stringify(value));
  } catch {
    return false;
  }
}
