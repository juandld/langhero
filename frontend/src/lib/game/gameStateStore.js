/**
 * Game State Store for LangHero.
 *
 * Centralizes game state (lives, score, etc.) with persistence
 * to localStorage and runStore. Used by GameView and ScenarioDisplay.
 */

import { writable, derived, get } from 'svelte/store';
import { browser } from '$app/environment';
import { updateRun, getRun } from '$lib/runStore.js';
import { STORAGE_KEYS } from '$lib/utils/storage';

/**
 * Create a game state store instance.
 * Each game session should have its own instance.
 */
export function createGameState() {
  // Core game state
  const lives = writable(3);
  const livesTotal = writable(3);
  const score = writable(0);
  const judgeFocus = writable(0);
  const languageOverride = writable('');

  // Tracking state
  const runId = writable(null);
  const trackRun = writable(false);
  const initialized = writable(false);

  // Feedback state
  const penaltyMessage = writable('');
  const lastHeard = writable('');
  const matchConfidence = writable(null);
  const matchType = writable('');

  // Last saved values (for dirty checking)
  let lastSaved = {
    score: null,
    lives: null,
    livesTotal: null,
    judgeFocus: null,
    languageOverride: null,
  };

  /**
   * Load state from a run object.
   */
  function loadFromRun(run) {
    if (!run) return;

    if (typeof run.score === 'number') {
      score.set(run.score);
      lastSaved.score = run.score;
    }
    if (typeof run.livesTotal === 'number') {
      livesTotal.set(Math.max(1, run.livesTotal));
      lastSaved.livesTotal = run.livesTotal;
    }
    if (typeof run.livesRemaining === 'number') {
      lives.set(Math.max(0, run.livesRemaining));
      lastSaved.lives = run.livesRemaining;
    }
    if (typeof run.judgeFocus === 'number') {
      judgeFocus.set(Math.max(0, Math.min(1, run.judgeFocus)));
      lastSaved.judgeFocus = run.judgeFocus;
    }
    if (run.languageOverride) {
      languageOverride.set(run.languageOverride);
      lastSaved.languageOverride = run.languageOverride;
    }

    initialized.set(true);
  }

  /**
   * Load state from localStorage (for settings that persist across runs).
   */
  function loadFromStorage() {
    if (!browser) return;

    try {
      const storedJudge = localStorage.getItem(STORAGE_KEYS.JUDGE_FOCUS);
      if (storedJudge !== null) {
        const parsed = parseFloat(storedJudge);
        if (Number.isFinite(parsed)) {
          judgeFocus.set(Math.max(0, Math.min(1, parsed)));
        }
      }
    } catch (_) {}

    try {
      const storedLang = localStorage.getItem(STORAGE_KEYS.LANGUAGE_OVERRIDE);
      if (storedLang) {
        languageOverride.set(storedLang);
      }
    } catch (_) {}
  }

  /**
   * Persist state to localStorage.
   */
  function persistToStorage() {
    if (!browser) return;

    try {
      localStorage.setItem(STORAGE_KEYS.JUDGE_FOCUS, String(get(judgeFocus)));
    } catch (_) {}

    try {
      localStorage.setItem(STORAGE_KEYS.LANGUAGE_OVERRIDE, get(languageOverride));
    } catch (_) {}
  }

  /**
   * Sync state to the run store (if tracking a run).
   */
  function syncToRun() {
    const currentRunId = get(runId);
    if (!get(trackRun) || !currentRunId) return;

    const updates = {};
    let hasUpdates = false;

    const currentScore = get(score);
    if (currentScore !== lastSaved.score) {
      updates.score = currentScore;
      lastSaved.score = currentScore;
      hasUpdates = true;
    }

    const currentLives = get(lives);
    if (currentLives !== lastSaved.lives) {
      updates.livesRemaining = currentLives;
      lastSaved.lives = currentLives;
      hasUpdates = true;
    }

    const currentLivesTotal = get(livesTotal);
    if (currentLivesTotal !== lastSaved.livesTotal) {
      updates.livesTotal = currentLivesTotal;
      lastSaved.livesTotal = currentLivesTotal;
      hasUpdates = true;
    }

    const currentJudge = get(judgeFocus);
    if (currentJudge !== lastSaved.judgeFocus) {
      updates.judgeFocus = currentJudge;
      lastSaved.judgeFocus = currentJudge;
      hasUpdates = true;
    }

    const currentLang = get(languageOverride);
    if (currentLang !== lastSaved.languageOverride) {
      updates.languageOverride = currentLang;
      lastSaved.languageOverride = currentLang;
      hasUpdates = true;
    }

    if (hasUpdates) {
      updateRun(currentRunId, updates);
    }
  }

  /**
   * Apply a state update (typically from streaming events).
   */
  function applyUpdate(update) {
    if (!update || typeof update !== 'object') return;

    if (typeof update.lives === 'number') {
      lives.set(Math.max(0, update.lives));
    } else if (typeof update.livesDelta === 'number') {
      lives.update(l => Math.max(0, l + update.livesDelta));
    }

    if (typeof update.livesTotal === 'number') {
      livesTotal.set(Math.max(1, update.livesTotal));
    }

    if (typeof update.score === 'number') {
      score.set(Math.max(0, update.score));
    }

    if (typeof update.penaltyMessage === 'string') {
      penaltyMessage.set(update.penaltyMessage);
    }

    if (update.runLivesInitialized) {
      initialized.set(true);
    }
  }

  /**
   * Apply interaction result.
   */
  function applyResult(result) {
    if (!result || typeof result !== 'object') return;

    if (result.heard) {
      lastHeard.set(result.heard);
    }

    const confidence = Number(result.confidence ?? result.match_confidence ?? result.matchConfidence);
    if (Number.isFinite(confidence)) {
      matchConfidence.set(Math.max(0, Math.min(1, confidence)));
    }

    if (result.match_type || result.matchType) {
      matchType.set(String(result.match_type ?? result.matchType ?? ''));
    }

    // Apply score/lives if present and not from stream (stream handles its own updates)
    if (typeof result.score === 'number') {
      score.set(Math.max(0, result.score));
    }
    if (typeof result.lives_total === 'number') {
      livesTotal.set(Math.max(1, result.lives_total));
    }
    if (typeof result.lives_remaining === 'number') {
      lives.set(Math.max(0, result.lives_remaining));
    }
  }

  /**
   * Reset lives to full.
   */
  function resetLives(total = 3) {
    livesTotal.set(total);
    lives.set(total);
  }

  /**
   * Add to score.
   */
  function addScore(points) {
    score.update(s => s + points);
  }

  /**
   * Deduct a life.
   */
  function loseLife(count = 1) {
    lives.update(l => Math.max(0, l - count));
  }

  /**
   * Set the run to track.
   */
  function setRun(id, shouldTrack = true) {
    runId.set(id);
    trackRun.set(shouldTrack);

    if (id && shouldTrack) {
      const run = getRun(id);
      if (run) {
        loadFromRun(run);
      }
    }
  }

  /**
   * Clear penalty message.
   */
  function clearPenalty() {
    penaltyMessage.set('');
  }

  /**
   * Get current state as object.
   */
  function getState() {
    return {
      lives: get(lives),
      livesTotal: get(livesTotal),
      score: get(score),
      judgeFocus: get(judgeFocus),
      languageOverride: get(languageOverride),
    };
  }

  // Derived store for checking if out of lives
  const isGameOver = derived(lives, $lives => $lives <= 0);

  return {
    // Stores
    lives,
    livesTotal,
    score,
    judgeFocus,
    languageOverride,
    penaltyMessage,
    lastHeard,
    matchConfidence,
    matchType,
    initialized,
    isGameOver,

    // Methods
    loadFromRun,
    loadFromStorage,
    persistToStorage,
    syncToRun,
    applyUpdate,
    applyResult,
    resetLives,
    addScore,
    loseLife,
    setRun,
    clearPenalty,
    getState,
  };
}

/**
 * Default singleton instance for simple use cases.
 */
export const gameState = createGameState();
