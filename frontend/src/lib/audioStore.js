/**
 * Audio Store - Global audio settings for LangHero.
 *
 * Provides shared volume and playback speed control across all components.
 * Persists to localStorage and survives page reloads.
 */
import { writable, get } from 'svelte/store';
import { browser } from '$app/environment';

const VOLUME_KEY = 'LANGHERO_VOLUME_V1';
const SPEED_KEY = 'LANGHERO_SPEED_V1';

// Load initial volume from localStorage (only on browser)
function loadInitialVolume() {
  if (!browser) return 1.0;
  try {
    const stored = localStorage.getItem(VOLUME_KEY);
    if (stored !== null) {
      const parsed = parseFloat(stored);
      if (!isNaN(parsed) && parsed >= 0 && parsed <= 1) {
        return parsed;
      }
    }
  } catch (_) {}
  return 1.0;
}

// Load initial playback speed from localStorage (default 1.25x for snappy feel)
function loadInitialSpeed() {
  if (!browser) return 1.25;
  try {
    const stored = localStorage.getItem(SPEED_KEY);
    if (stored !== null) {
      const parsed = parseFloat(stored);
      if (!isNaN(parsed) && parsed >= 0.5 && parsed <= 2.0) {
        return parsed;
      }
    }
  } catch (_) {}
  return 1.25;
}

// Create the stores with initial values
export const masterVolume = writable(loadInitialVolume());
export const playbackSpeed = writable(loadInitialSpeed());

// On browser, re-load from localStorage (handles SSR hydration)
if (browser) {
  const storedVolume = loadInitialVolume();
  const storedSpeed = loadInitialSpeed();
  masterVolume.set(storedVolume);
  playbackSpeed.set(storedSpeed);
}

// Subscribe to changes and persist to localStorage
masterVolume.subscribe((value) => {
  if (!browser) return;
  try {
    localStorage.setItem(VOLUME_KEY, String(value));
  } catch (_) {}
});

playbackSpeed.subscribe((value) => {
  if (!browser) return;
  try {
    localStorage.setItem(SPEED_KEY, String(value));
  } catch (_) {}
});

/**
 * Set the master volume (0.0 - 1.0)
 */
export function setVolume(value) {
  const clamped = Math.max(0, Math.min(1, value));
  masterVolume.set(clamped);
}

/**
 * Get the current master volume
 */
export function getVolume() {
  return get(masterVolume);
}

/**
 * Set the playback speed (0.5 - 2.0)
 */
export function setSpeed(value) {
  const clamped = Math.max(0.5, Math.min(2.0, value));
  playbackSpeed.set(clamped);
}

/**
 * Get the current playback speed
 */
export function getSpeed() {
  return get(playbackSpeed);
}

/**
 * Create an Audio element with the current master volume applied
 */
export function createAudio(src) {
  const audio = new Audio(src);
  audio.volume = get(masterVolume);

  // Subscribe to volume changes
  const unsub = masterVolume.subscribe((vol) => {
    audio.volume = vol;
  });

  // Clean up subscription when audio is done
  const originalOnended = audio.onended;
  audio.onended = (e) => {
    unsub();
    if (originalOnended) originalOnended.call(audio, e);
  };

  return audio;
}
