import { writable, get } from 'svelte/store';

/**
 * @typedef {import('./storyStore.js').Scenario} Scenario
 */

/**
 * @typedef {Object} SavedRun
 * @property {string} id
 * @property {string} title
 * @property {string} [targetLanguage]
 * @property {number} createdAt
 * @property {number} updatedAt
 * @property {number} totalPlayMs
 * @property {number} currentScenarioId
 * @property {number} [score]
 * @property {number} [livesTotal]
 * @property {number} [livesRemaining]
 * @property {number} [judgeFocus]
 * @property {string} [languageOverride]
 * @property {string} [publishedPublicId]
 * @property {string} [publishedDeleteKey]
 * @property {number} [publishedAt]
 * @property {Scenario[]} scenarios
 */

const RUNS_KEY = 'LANGHERO_SAVED_RUNS_V1';
const ACTIVE_KEY = 'LANGHERO_ACTIVE_RUN_ID_V1';

/** @type {SavedRun[]} */
let cache = [];
let initialized = false;

export const runsStore = writable(/** @type {SavedRun[]} */ ([]));
export const activeRunId = writable(/** @type {string | null} */ (null));

function hasWindow() {
  return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';
}

function safeParseJson(value) {
  try {
    return JSON.parse(value);
  } catch (_) {
    return null;
  }
}

function toStringId(value) {
  if (typeof value === 'string' && value.trim()) return value.trim();
  return null;
}

function nowMs() {
  return Date.now();
}

function uuid() {
  try {
    if (hasWindow() && typeof window.crypto?.randomUUID === 'function') return window.crypto.randomUUID();
  } catch (_) {}
  return `${nowMs()}-${Math.random().toString(16).slice(2)}`;
}

/**
 * @param {any} candidate
 * @returns {candidate is SavedRun}
 */
function isSavedRun(candidate) {
  return Boolean(
    candidate &&
      typeof candidate === 'object' &&
      typeof candidate.id === 'string' &&
      typeof candidate.title === 'string' &&
      typeof candidate.createdAt === 'number' &&
      typeof candidate.updatedAt === 'number' &&
      typeof candidate.totalPlayMs === 'number' &&
      typeof candidate.currentScenarioId === 'number' &&
      Array.isArray(candidate.scenarios),
  );
}

function persist() {
  if (!hasWindow()) return;
  try {
    window.localStorage.setItem(RUNS_KEY, JSON.stringify(cache));
  } catch (_) {}
  try {
    const active = get(activeRunId);
    if (active) window.localStorage.setItem(ACTIVE_KEY, active);
    else window.localStorage.removeItem(ACTIVE_KEY);
  } catch (_) {}
}

function ensureInit() {
  if (initialized) return;
  initialized = true;
  if (!hasWindow()) {
    cache = [];
    runsStore.set(cache);
    activeRunId.set(null);
    return;
  }
  try {
    const raw = window.localStorage.getItem(RUNS_KEY);
    const parsed = safeParseJson(raw || '[]');
    if (Array.isArray(parsed)) {
      cache = parsed.filter(isSavedRun);
    } else {
      cache = [];
    }
  } catch (_) {
    cache = [];
  }
  runsStore.set(cache);
  try {
    const active = toStringId(window.localStorage.getItem(ACTIVE_KEY));
    activeRunId.set(active);
  } catch (_) {
    activeRunId.set(null);
  }
}

/**
 * @returns {SavedRun[]}
 */
export function getRuns() {
  ensureInit();
  return cache.slice();
}

/**
 * @param {string} id
 * @returns {SavedRun | null}
 */
export function getRun(id) {
  ensureInit();
  const rid = toStringId(id);
  if (!rid) return null;
  return cache.find((r) => r.id === rid) || null;
}

/**
 * @param {string | null} id
 */
export function setActiveRun(id) {
  ensureInit();
  const rid = toStringId(id);
  activeRunId.set(rid);
  persist();
}

/**
 * @param {SavedRun} run
 */
function upsert(run) {
  const idx = cache.findIndex((r) => r.id === run.id);
  if (idx >= 0) {
    cache = [...cache.slice(0, idx), run, ...cache.slice(idx + 1)];
  } else {
    cache = [run, ...cache];
  }
  runsStore.set(cache);
  persist();
}

/**
 * @param {{ title?: string, targetLanguage?: string, scenarios: Scenario[], startId?: number }} args
 * @returns {SavedRun}
 */
export function createRun(args) {
  ensureInit();
  const scenarios = Array.isArray(args?.scenarios) ? args.scenarios : [];
  const first = scenarios.find((s) => s && typeof s === 'object' && typeof s.id === 'number') || null;
  const initialLivesTotal = (() => {
    const raw = Number(first?.lives ?? first?.max_lives ?? first?.lives_total);
    if (Number.isFinite(raw) && raw > 0) return Math.floor(raw);
    return 3;
  })();
  const id = uuid();
  const createdAt = nowMs();
  const startId =
    typeof args?.startId === 'number'
      ? args.startId
      : typeof first?.id === 'number'
        ? first.id
        : 1;
  /** @type {SavedRun} */
  const run = {
    id,
    title: String(args?.title || 'Untitled run'),
    targetLanguage: args?.targetLanguage ? String(args.targetLanguage) : first?.language || '',
    createdAt,
    updatedAt: createdAt,
    totalPlayMs: 0,
    currentScenarioId: startId,
    score: 0,
    livesTotal: initialLivesTotal,
    livesRemaining: initialLivesTotal,
    judgeFocus: 0,
    languageOverride: '',
    publishedPublicId: '',
    publishedDeleteKey: '',
    publishedAt: 0,
    scenarios,
  };
  upsert(run);
  setActiveRun(id);
  return run;
}

/**
 * @param {string} id
 */
export function deleteRun(id) {
  ensureInit();
  const rid = toStringId(id);
  if (!rid) return;
  cache = cache.filter((r) => r.id !== rid);
  runsStore.set(cache);
  if (get(activeRunId) === rid) setActiveRun(null);
  persist();
}

/**
 * @param {string} id
 * @param {Partial<SavedRun>} patch
 * @returns {SavedRun | null}
 */
export function updateRun(id, patch) {
  ensureInit();
  const rid = toStringId(id);
  if (!rid) return null;
  const existing = getRun(rid);
  if (!existing) return null;
  /** @type {SavedRun} */
  const next = {
    ...existing,
    ...patch,
    id: existing.id,
    createdAt: existing.createdAt,
    updatedAt: nowMs(),
  };
  upsert(next);
  return next;
}

/**
 * @param {string} id
 * @param {number} deltaMs
 */
export function addPlayTime(id, deltaMs) {
  ensureInit();
  const rid = toStringId(id);
  if (!rid) return;
  const run = getRun(rid);
  if (!run) return;
  const delta = Number.isFinite(deltaMs) ? Math.max(0, Math.floor(deltaMs)) : 0;
  if (!delta) return;
  updateRun(rid, { totalPlayMs: (run.totalPlayMs || 0) + delta });
}

/**
 * Ensure we have loaded storage into the in-memory cache/stores.
 * Useful to call from page onMount before reading.
 */
export function syncFromStorage() {
  ensureInit();
  runsStore.set(cache);
}
