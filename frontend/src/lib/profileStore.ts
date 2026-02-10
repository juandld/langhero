import { writable, derived, get } from 'svelte/store';

// ========== Types ==========

export interface StylePoints {
  polite: number;
  direct: number;
  tricky: number;
  charming: number;
  bold: number;
  humble: number;
  evasive: number;
  respectful: number;
  casual: number;
  rude: number;
}

export interface PlayerProfile {
  rank: string;
  rankProgress: number;  // 0-100% to next rank
  scenariosCompleted: number;
  styles: StylePoints;
  dominantStyle: string | null;
  badge: string | null;
  currentStreak: number;
  lastPracticeDate: string | null;
}

// ========== Constants ==========

const STORAGE_KEY = 'LANGHERO_PROFILE_V1';

const RANKS = [
  { name: 'Pelele', threshold: 0 },
  { name: 'Apprentice', threshold: 5 },
  { name: 'Conversant', threshold: 15 },
  { name: 'Negotiator', threshold: 30 },
  { name: 'Silver Tongue', threshold: 50 },
  { name: 'Master', threshold: 100 },
] as const;

const BADGES: Record<string, string> = {
  polite: 'The Diplomat',
  direct: 'The Straight Shooter',
  tricky: 'The Trickster',
  charming: 'The Smooth Talker',
  bold: 'The Bold One',
  humble: 'The Gracious',
  evasive: 'The Elusive',
  respectful: 'The Reverent',
  casual: 'The Easygoing',
  rude: 'The Blunt One',
};

// ========== Initial State ==========

function createInitialProfile(): PlayerProfile {
  return {
    rank: 'Pelele',
    rankProgress: 0,
    scenariosCompleted: 0,
    styles: {
      polite: 0,
      direct: 0,
      tricky: 0,
      charming: 0,
      bold: 0,
      humble: 0,
      evasive: 0,
      respectful: 0,
      casual: 0,
      rude: 0,
    },
    dominantStyle: null,
    badge: null,
    currentStreak: 0,
    lastPracticeDate: null,
  };
}

function loadFromStorage(): PlayerProfile {
  if (typeof localStorage === 'undefined') {
    return createInitialProfile();
  }
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      // Merge with initial to ensure all fields exist
      return { ...createInitialProfile(), ...parsed };
    }
  } catch (e) {
    console.warn('Failed to load profile from storage:', e);
  }
  return createInitialProfile();
}

function saveToStorage(profile: PlayerProfile): void {
  if (typeof localStorage === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(profile));
  } catch (e) {
    console.warn('Failed to save profile to storage:', e);
  }
}

// ========== Computed Helpers ==========

function computeRank(scenariosCompleted: number): { rank: string; progress: number } {
  let currentRank = RANKS[0];
  let nextRank = RANKS[1] || null;

  for (let i = 0; i < RANKS.length; i++) {
    if (scenariosCompleted >= RANKS[i].threshold) {
      currentRank = RANKS[i];
      nextRank = RANKS[i + 1] || null;
    }
  }

  let progress = 100;
  if (nextRank) {
    const rangeStart = currentRank.threshold;
    const rangeEnd = nextRank.threshold;
    const rangeSize = rangeEnd - rangeStart;
    const completed = scenariosCompleted - rangeStart;
    progress = Math.min(100, Math.max(0, Math.round((completed / rangeSize) * 100)));
  }

  return { rank: currentRank.name, progress };
}

function computeDominantStyle(styles: StylePoints): string | null {
  let maxStyle: string | null = null;
  let maxPoints = 0;

  for (const [style, points] of Object.entries(styles)) {
    if (points > maxPoints) {
      maxPoints = points;
      maxStyle = style;
    }
  }

  return maxPoints > 0 ? maxStyle : null;
}

function computeBadge(dominantStyle: string | null): string | null {
  if (!dominantStyle) return null;
  return BADGES[dominantStyle] || null;
}

function checkAndUpdateStreak(profile: PlayerProfile): PlayerProfile {
  const today = new Date().toISOString().split('T')[0];
  const lastDate = profile.lastPracticeDate;

  if (!lastDate) {
    return { ...profile, currentStreak: 1, lastPracticeDate: today };
  }

  if (lastDate === today) {
    return profile; // Already practiced today
  }

  const yesterday = new Date(Date.now() - 86400000).toISOString().split('T')[0];
  if (lastDate === yesterday) {
    return { ...profile, currentStreak: profile.currentStreak + 1, lastPracticeDate: today };
  }

  // Streak broken
  return { ...profile, currentStreak: 1, lastPracticeDate: today };
}

// ========== Store ==========

function createProfileStore() {
  const { subscribe, set, update } = writable<PlayerProfile>(loadFromStorage());

  return {
    subscribe,

    // Complete a scenario and optionally add style points
    completeScenario(styleGained?: string | null, stylePoints: number = 1) {
      update(profile => {
        const newProfile = { ...profile };
        newProfile.scenariosCompleted += 1;

        // Add style points if applicable
        if (styleGained && styleGained in newProfile.styles) {
          (newProfile.styles as any)[styleGained] += stylePoints;
        }

        // Recompute rank
        const { rank, progress } = computeRank(newProfile.scenariosCompleted);
        const previousRank = newProfile.rank;
        newProfile.rank = rank;
        newProfile.rankProgress = progress;

        // Recompute badge
        newProfile.dominantStyle = computeDominantStyle(newProfile.styles);
        newProfile.badge = computeBadge(newProfile.dominantStyle);

        // Update streak
        const updatedProfile = checkAndUpdateStreak(newProfile);

        // Save to storage
        saveToStorage(updatedProfile);

        // Return rank up info if applicable
        if (rank !== previousRank) {
          // Dispatch custom event for rank up celebration
          if (typeof window !== 'undefined') {
            window.dispatchEvent(new CustomEvent('langhero:rankup', {
              detail: { newRank: rank, previousRank }
            }));
          }
        }

        return updatedProfile;
      });
    },

    // Add style points without completing scenario
    addStylePoints(style: string, points: number = 1) {
      update(profile => {
        if (!(style in profile.styles)) return profile;

        const newProfile = { ...profile };
        (newProfile.styles as any)[style] += points;
        newProfile.dominantStyle = computeDominantStyle(newProfile.styles);
        newProfile.badge = computeBadge(newProfile.dominantStyle);
        saveToStorage(newProfile);
        return newProfile;
      });
    },

    // Reset profile
    reset() {
      const initial = createInitialProfile();
      set(initial);
      saveToStorage(initial);
    },

    // Get current profile snapshot
    getSnapshot(): PlayerProfile {
      return get({ subscribe });
    },

    // Hydrate from storage (useful for SSR)
    hydrate() {
      set(loadFromStorage());
    },
  };
}

export const profileStore = createProfileStore();

// ========== Derived Stores ==========

export const currentRank = derived(profileStore, $profile => $profile.rank);
export const currentBadge = derived(profileStore, $profile => $profile.badge);
export const rankProgress = derived(profileStore, $profile => $profile.rankProgress);
export const displayTitle = derived(profileStore, $profile => {
  if ($profile.badge) {
    return `${$profile.rank} - ${$profile.badge}`;
  }
  return $profile.rank;
});
export const scenariosCompleted = derived(profileStore, $profile => $profile.scenariosCompleted);
export const currentStreak = derived(profileStore, $profile => $profile.currentStreak);
