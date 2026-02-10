<script>
  /**
   * LangHero Main Menu
   *
   * An immersive, animated video game-style title screen that sets the tone
   * for the time-traveling language learning adventure.
   *
   * Mobile-first: Touch interactions work via tap-to-select, tap-again-to-go.
   */
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { fade, fly, scale } from 'svelte/transition';
  import { cubicOut } from 'svelte/easing';
  import { runsStore, syncFromStorage } from '$lib/runStore.js';
  import { authUser, hydrateAuth, isAppwriteConfigured } from '$lib/auth';

  // Animation states
  let mounted = false;
  let showTitle = false;
  let showSubtitle = false;
  let showMenu = false;
  let showParticles = false;

  // Modal state
  let showStartNewModal = false;

  // Touch/interaction state
  let selectedOption = null;  // For mobile: tap to select, tap again to navigate
  let hoveredOption = null;   // For desktop: hover to preview
  let isTouchDevice = false;

  // Auth state
  let authChecked = false;
  $: isLoggedIn = $authUser !== null;

  // Story progress key (same as storyManager)
  const STORY_PROGRESS_KEY = 'LANGHERO_STORY_PROGRESS_V1';

  // Check for story progress
  function hasStoryProgress() {
    try {
      const saved = localStorage.getItem(STORY_PROGRESS_KEY);
      if (!saved) return false;
      const progress = JSON.parse(saved);
      // Check if any story has meaningful progress
      return Object.values(progress).some(p =>
        p && (p.state === 'playing' || p.tutorialCompleted)
      );
    } catch {
      return false;
    }
  }

  // Check for existing saves
  $: hasSaves = $runsStore && $runsStore.length > 0;
  $: saveCount = $runsStore?.length || 0;

  // Check for story progress (re-evaluated on mount)
  let hasProgress = false;

  // Dynamic descriptions based on auth/progress state
  $: descriptions = {
    story: {
      title: hasProgress ? 'Continue Your Journey' : 'Begin Your Journey',
      text: hasProgress
        ? 'Return to 1600 Japan. Your progress awaits. Pick up where you left off in your adventure.'
        : 'Travel back to 1600 Japan. Learn Japanese by surviving as a shipwrecked stranger in the age of samurai. Your words are your weapon.',
      extra: hasProgress ? 'Resume story mode' : 'Full story mode with tutorial',
      subtitle: hasProgress ? 'Continue your adventure' : 'Travel to 1600 Japan',
    },
    startNew: {
      title: 'Start Fresh',
      text: 'Begin a new journey from the beginning. Your current story progress will be reset.',
      extra: 'New game',
      subtitle: 'Start over from scratch',
    },
    continue: {
      title: 'Continue Adventure',
      text: 'Pick up where you left off. Your progress, vocabulary, and story choices are waiting for you.',
      extra: 'Resume your last session',
      subtitle: 'Resume your adventure',
    },
    practice: {
      title: 'Quick Practice',
      text: 'Jump straight into conversation scenarios. Perfect for warming up or practicing specific phrases without the story.',
      extra: 'No commitment, just practice',
      subtitle: 'Practice without story',
    },
    saves: {
      title: 'Saved Adventures',
      text: 'View all your saved game runs. Manage, share, or delete your previous adventures.',
      extra: `${saveCount} save${saveCount !== 1 ? 's' : ''} available`,
      subtitle: 'Manage saved games',
    },
    import: {
      title: 'Import Your Own Story',
      text: 'Bring your own content. Paste text, a URL, or a video link and we\'ll turn it into an interactive language lesson.',
      extra: 'Create custom scenarios',
      subtitle: 'Create from any content',
    },
    login: {
      title: isLoggedIn ? 'Your Account' : 'Sign In',
      text: isLoggedIn
        ? 'View your profile, achievements, and manage your account settings.'
        : 'Sign in to sync your progress across devices, unlock achievements, and join the community.',
      extra: isLoggedIn ? 'Profile & settings' : 'Sync & social features',
      subtitle: isLoggedIn ? 'View profile' : 'Sign in or create account',
    },
  };

  // Show description from either touch selection or hover
  $: activeOption = selectedOption || hoveredOption;
  $: currentDescription = activeOption ? descriptions[activeOption] : null;

  onMount(async () => {
    syncFromStorage();
    mounted = true;

    // Check auth state
    if (isAppwriteConfigured()) {
      try {
        await hydrateAuth();
      } catch {
        // Auth failed, continue as logged out
      }
    }
    authChecked = true;

    // Check for story progress
    hasProgress = hasStoryProgress();

    // Detect touch device
    isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;

    // Staggered entrance animations
    setTimeout(() => showParticles = true, 100);
    setTimeout(() => showTitle = true, 400);
    setTimeout(() => showSubtitle = true, 900);
    setTimeout(() => showMenu = true, 1400);
  });

  // Clear story progress for fresh start
  function clearStoryProgress() {
    try {
      localStorage.removeItem(STORY_PROGRESS_KEY);
    } catch {
      // Ignore errors
    }
  }

  // Navigation functions
  const navigateTo = {
    story: () => goto('/story'),
    startNew: () => {
      if (hasProgress) {
        showStartNewModal = true;
      } else {
        goto('/story');
      }
    },
    continue: () => {
      if ($runsStore?.length) {
        const mostRecent = $runsStore[0];
        goto(`/play/${encodeURIComponent(mostRecent.id)}`);
      }
    },
    practice: () => goto('/demo'),
    saves: () => goto('/menu'),
    import: () => goto('/import'),
    login: () => goto('/login'),
  };

  // Confirm starting new game
  function confirmStartNew() {
    clearStoryProgress();
    hasProgress = false;
    showStartNewModal = false;
    goto('/story');
  }

  // Cancel start new modal
  function cancelStartNew() {
    showStartNewModal = false;
  }

  function handleButtonClick(option, event) {
    // Stop propagation so backdrop handler doesn't clear selection
    event?.stopPropagation();

    if (isTouchDevice) {
      // Touch device: tap to select, tap again to navigate
      if (selectedOption === option) {
        // Second tap - navigate
        navigateTo[option]?.();
      } else {
        // First tap - select and show description
        selectedOption = option;
      }
    } else {
      // Desktop: click navigates immediately
      navigateTo[option]?.();
    }
  }

  function handleMenuTouch(e) {
    // If user taps outside buttons on mobile, clear selection
    if (e.target.classList.contains('menu-container') ||
        e.target.classList.contains('menu-options')) {
      selectedOption = null;
    }
  }

  // Desktop hover handlers
  function handleMouseEnter(option) {
    if (!isTouchDevice) {
      hoveredOption = option;
    }
  }

  function handleMouseLeave() {
    if (!isTouchDevice) {
      hoveredOption = null;
    }
  }

  // Clear selection when tapping backdrop
  function handleBackdropTouch() {
    selectedOption = null;
  }

  // Generate floating particles
  const particles = Array.from({ length: 30 }, (_, i) => ({
    id: i,
    x: Math.random() * 100,
    y: Math.random() * 100,
    size: 2 + Math.random() * 4,
    duration: 15 + Math.random() * 20,
    delay: Math.random() * 10,
    opacity: 0.2 + Math.random() * 0.4,
  }));

  // Kanji that float in the background
  const floatingKanji = ['時', '旅', '学', '道', '心', '言', '葉', '夢'];
</script>

<svelte:head>
  <title>LangHero - Learn Through Time</title>
</svelte:head>

<!-- svelte-ignore a11y-click-events-have-key-events -->
<!-- svelte-ignore a11y-no-static-element-interactions -->
<main class="main-menu" on:click={handleBackdropTouch}>
  <!-- Animated Background Layers -->
  <div class="bg-layer bg-stars"></div>
  <div class="bg-layer bg-nebula"></div>
  <div class="bg-layer bg-vignette"></div>

  <!-- Floating Particles -->
  {#if showParticles}
    <div class="particles-container" in:fade={{ duration: 2000 }}>
      {#each particles as p (p.id)}
        <div
          class="particle"
          style="
            left: {p.x}%;
            top: {p.y}%;
            width: {p.size}px;
            height: {p.size}px;
            opacity: {p.opacity};
            animation-duration: {p.duration}s;
            animation-delay: {p.delay}s;
          "
        ></div>
      {/each}
    </div>

    <!-- Floating Kanji -->
    <div class="kanji-container">
      {#each floatingKanji as kanji, i}
        <div
          class="floating-kanji"
          style="
            left: {10 + i * 11}%;
            animation-delay: {i * 2}s;
            animation-duration: {25 + i * 3}s;
          "
        >{kanji}</div>
      {/each}
    </div>
  {/if}

  <!-- Bimbo Orb (AI Companion hint) -->
  <div class="orb-container">
    <div class="orb-glow"></div>
    <div class="orb-core"></div>
    <div class="orb-ring"></div>
  </div>

  <!-- Main Content -->
  <div class="content">
    <!-- Logo / Title -->
    {#if showTitle}
      <div class="title-container" in:fly={{ y: -40, duration: 1000, easing: cubicOut }}>
        <h1 class="game-title">
          <span class="title-lang">Lang</span><span class="title-hero">Hero</span>
        </h1>
        <div class="title-glow"></div>
      </div>
    {/if}

    <!-- Subtitle / Tagline -->
    {#if showSubtitle}
      <p class="tagline" in:fade={{ duration: 800 }}>
        Learn Through Time
      </p>
      <p class="description" in:fade={{ duration: 800, delay: 200 }}>
        Master languages through immersive time-travel adventures
      </p>
    {/if}

    <!-- Menu Container -->
    {#if showMenu}
      <div class="menu-container" in:fade={{ duration: 600 }}>
        <!-- Menu Options -->
        <!-- svelte-ignore a11y-click-events-have-key-events -->
        <!-- svelte-ignore a11y-no-static-element-interactions -->
        <nav class="menu-options" on:click={handleMenuTouch}>
          <!-- Primary CTA - Shows "Continue" if has progress, "Begin Journey" otherwise -->
          <button
            class="menu-btn primary"
            class:active={activeOption === 'story'}
            class:selected={selectedOption === 'story'}
            on:click={(e) => handleButtonClick('story', e)}
            on:mouseenter={() => handleMouseEnter('story')}
            on:mouseleave={handleMouseLeave}
            on:focus={() => handleMouseEnter('story')}
            on:blur={handleMouseLeave}
            in:fly={{ y: 30, duration: 500, delay: 0 }}
          >
            <span class="btn-icon">
              <svg viewBox="0 0 24 24" fill="currentColor">
                {#if hasProgress}
                  <path d="M8 5v14l11-7z"/>
                {:else}
                  <path d="M8 5v14l11-7z"/>
                {/if}
              </svg>
            </span>
            <span class="btn-text">
              <span class="btn-label">{hasProgress ? 'Continue Journey' : 'Begin Journey'}</span>
              <span class="btn-subtitle">{descriptions.story.subtitle}</span>
            </span>
            <span class="btn-arrow">{selectedOption === 'story' ? 'Go →' : '→'}</span>
          </button>

          <!-- Start New (only shows if has progress) -->
          {#if hasProgress}
            <button
              class="menu-btn secondary start-new"
              class:active={activeOption === 'startNew'}
              class:selected={selectedOption === 'startNew'}
              on:click={(e) => handleButtonClick('startNew', e)}
              on:mouseenter={() => handleMouseEnter('startNew')}
              on:mouseleave={handleMouseLeave}
              on:focus={() => handleMouseEnter('startNew')}
              on:blur={handleMouseLeave}
              in:fly={{ y: 30, duration: 500, delay: 100 }}
            >
              <span class="btn-icon">
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 5V1L7 6l5 5V7c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6H4c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z"/>
                </svg>
              </span>
              <span class="btn-text">
                <span class="btn-label">Start New</span>
                <span class="btn-subtitle">{descriptions.startNew.subtitle}</span>
              </span>
              {#if selectedOption === 'startNew'}
                <span class="btn-arrow">Go →</span>
              {/if}
            </button>
          {/if}

          <!-- Continue (if saves exist) -->
          {#if hasSaves}
            <button
              class="menu-btn secondary"
              class:active={activeOption === 'continue'}
              class:selected={selectedOption === 'continue'}
              on:click={(e) => handleButtonClick('continue', e)}
              on:mouseenter={() => handleMouseEnter('continue')}
              on:mouseleave={handleMouseLeave}
              on:focus={() => handleMouseEnter('continue')}
              on:blur={handleMouseLeave}
              in:fly={{ y: 30, duration: 500, delay: 100 }}
            >
              <span class="btn-icon">
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/>
                </svg>
              </span>
              <span class="btn-text">
                <span class="btn-label">Continue</span>
                <span class="btn-subtitle">{descriptions.continue.subtitle}</span>
              </span>
              {#if selectedOption === 'continue'}
                <span class="btn-arrow">Go →</span>
              {/if}
            </button>
          {/if}

          <!-- Quick Practice -->
          <button
            class="menu-btn tertiary"
            class:active={activeOption === 'practice'}
            class:selected={selectedOption === 'practice'}
            on:click={(e) => handleButtonClick('practice', e)}
            on:mouseenter={() => handleMouseEnter('practice')}
            on:mouseleave={handleMouseLeave}
            on:focus={() => handleMouseEnter('practice')}
            on:blur={handleMouseLeave}
            in:fly={{ y: 30, duration: 500, delay: hasSaves ? 200 : 100 }}
          >
            <span class="btn-icon">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/>
              </svg>
            </span>
            <span class="btn-text">
              <span class="btn-label">Quick Practice</span>
              <span class="btn-subtitle">{descriptions.practice.subtitle}</span>
            </span>
            {#if selectedOption === 'practice'}
              <span class="btn-arrow">Go →</span>
            {/if}
          </button>

          <!-- Saved Runs -->
          {#if hasSaves}
            <button
              class="menu-btn tertiary"
              class:active={activeOption === 'saves'}
              class:selected={selectedOption === 'saves'}
              on:click={(e) => handleButtonClick('saves', e)}
              on:mouseenter={() => handleMouseEnter('saves')}
              on:mouseleave={handleMouseLeave}
              on:focus={() => handleMouseEnter('saves')}
              on:blur={handleMouseLeave}
              in:fly={{ y: 30, duration: 500, delay: 300 }}
            >
              <span class="btn-icon">
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <path d="M17 3H7c-1.1 0-2 .9-2 2v16l7-3 7 3V5c0-1.1-.9-2-2-2z"/>
                </svg>
              </span>
              <span class="btn-text">
                <span class="btn-label">Saved Runs</span>
                <span class="btn-subtitle">{descriptions.saves.subtitle}</span>
              </span>
              <span class="btn-badge">{saveCount}</span>
              {#if selectedOption === 'saves'}
                <span class="btn-arrow">Go →</span>
              {/if}
            </button>
          {/if}

          <!-- Divider -->
          <div class="menu-divider" in:fly={{ y: 30, duration: 500, delay: hasSaves ? 400 : 200 }}></div>

          <!-- Import Story -->
          <button
            class="menu-btn compact"
            class:active={activeOption === 'import'}
            class:selected={selectedOption === 'import'}
            on:click={(e) => handleButtonClick('import', e)}
            on:mouseenter={() => handleMouseEnter('import')}
            on:mouseleave={handleMouseLeave}
            on:focus={() => handleMouseEnter('import')}
            on:blur={handleMouseLeave}
            in:fly={{ y: 30, duration: 500, delay: hasSaves ? 450 : 250 }}
          >
            <span class="btn-icon small">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
              </svg>
            </span>
            <span class="btn-text">
              <span class="btn-label">Import Story</span>
              <span class="btn-subtitle">{descriptions.import.subtitle}</span>
            </span>
            {#if selectedOption === 'import'}
              <span class="btn-arrow">Go →</span>
            {/if}
          </button>

          <!-- Login / Account -->
          <button
            class="menu-btn compact"
            class:active={activeOption === 'login'}
            class:selected={selectedOption === 'login'}
            on:click={(e) => handleButtonClick('login', e)}
            on:mouseenter={() => handleMouseEnter('login')}
            on:mouseleave={handleMouseLeave}
            on:focus={() => handleMouseEnter('login')}
            on:blur={handleMouseLeave}
            in:fly={{ y: 30, duration: 500, delay: hasSaves ? 500 : 300 }}
          >
            <span class="btn-icon small">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
              </svg>
            </span>
            <span class="btn-text">
              <span class="btn-label">Account</span>
              <span class="btn-subtitle">{descriptions.login.subtitle}</span>
            </span>
            {#if selectedOption === 'login'}
              <span class="btn-arrow">Go →</span>
            {/if}
          </button>
        </nav>

        <!-- Description Panel (desktop shows on side, mobile shows below) -->
        <div class="description-panel" class:visible={currentDescription}>
          {#if currentDescription}
            <div class="desc-content" in:fade={{ duration: 200 }} out:fade={{ duration: 150 }}>
              <h3 class="desc-title">{currentDescription.title}</h3>
              <p class="desc-text">{currentDescription.text}</p>
              <span class="desc-extra">{currentDescription.extra}</span>
              {#if selectedOption}
                <p class="desc-tap-hint">Tap again to start</p>
              {/if}
            </div>
          {:else}
            <div class="desc-placeholder" in:fade={{ duration: 200 }}>
              <p class="desktop-hint">Hover over an option to learn more</p>
              <p class="mobile-hint">Tap an option to see details</p>
            </div>
          {/if}
        </div>
      </div>
    {/if}
  </div>

  <!-- Bottom Version -->
  {#if showMenu}
    <footer class="footer" in:fade={{ duration: 600, delay: 400 }}>
      <p class="version">Early Access</p>
    </footer>
  {/if}

  <!-- Hover Effect Backdrop -->
  {#if activeOption === 'story'}
    <div class="hover-backdrop story" in:fade={{ duration: 300 }} out:fade={{ duration: 200 }}></div>
  {/if}

  <!-- Start New Confirmation Modal -->
  {#if showStartNewModal}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div class="modal-overlay" on:click={cancelStartNew} transition:fade={{ duration: 200 }}>
      <div
        class="modal-content"
        on:click|stopPropagation
        transition:scale={{ duration: 300, start: 0.9, easing: cubicOut }}
      >
        <h2 class="modal-title">Start Fresh?</h2>
        <p class="modal-text">
          This will reset your story progress. You'll start from the beginning with the tutorial.
        </p>
        <p class="modal-warning">
          Your practice runs and saved scenarios will be kept.
        </p>
        <div class="modal-actions">
          <button class="modal-btn cancel" on:click={cancelStartNew}>
            Cancel
          </button>
          <button class="modal-btn confirm" on:click={confirmStartNew}>
            Start New Game
          </button>
        </div>
      </div>
    </div>
  {/if}
</main>

<style>
  /* ============================================
     BASE STYLES
     ============================================ */
  .main-menu {
    position: fixed;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    background: #050510;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  }

  /* ============================================
     BACKGROUND LAYERS
     ============================================ */
  .bg-layer {
    position: absolute;
    inset: 0;
    pointer-events: none;
  }

  .bg-stars {
    background:
      radial-gradient(1px 1px at 20% 30%, rgba(255,255,255,0.8), transparent),
      radial-gradient(1px 1px at 40% 70%, rgba(255,255,255,0.6), transparent),
      radial-gradient(1px 1px at 50% 50%, rgba(255,255,255,0.5), transparent),
      radial-gradient(2px 2px at 60% 20%, rgba(255,255,255,0.7), transparent),
      radial-gradient(1px 1px at 70% 60%, rgba(255,255,255,0.6), transparent),
      radial-gradient(1px 1px at 80% 40%, rgba(255,255,255,0.5), transparent),
      radial-gradient(1px 1px at 90% 80%, rgba(255,255,255,0.4), transparent),
      radial-gradient(2px 2px at 15% 80%, rgba(255,255,255,0.6), transparent),
      radial-gradient(1px 1px at 25% 10%, rgba(255,255,255,0.5), transparent),
      radial-gradient(1px 1px at 85% 15%, rgba(255,255,255,0.4), transparent);
    background-size: 200% 200%;
    animation: stars-drift 60s linear infinite;
  }

  @keyframes stars-drift {
    from { background-position: 0% 0%; }
    to { background-position: 100% 100%; }
  }

  .bg-nebula {
    background:
      radial-gradient(ellipse at 20% 80%, rgba(139, 92, 246, 0.15) 0%, transparent 50%),
      radial-gradient(ellipse at 80% 20%, rgba(59, 130, 246, 0.12) 0%, transparent 50%),
      radial-gradient(ellipse at 50% 50%, rgba(99, 102, 241, 0.08) 0%, transparent 60%);
    animation: nebula-pulse 15s ease-in-out infinite alternate;
  }

  @keyframes nebula-pulse {
    from { opacity: 0.6; transform: scale(1); }
    to { opacity: 1; transform: scale(1.05); }
  }

  .bg-vignette {
    background: radial-gradient(ellipse at center, transparent 0%, rgba(5, 5, 16, 0.4) 60%, rgba(5, 5, 16, 0.9) 100%);
  }

  /* ============================================
     PARTICLES
     ============================================ */
  .particles-container {
    position: absolute;
    inset: 0;
    pointer-events: none;
    overflow: hidden;
  }

  .particle {
    position: absolute;
    background: radial-gradient(circle, rgba(139, 92, 246, 0.8), transparent 70%);
    border-radius: 50%;
    animation: particle-float linear infinite;
  }

  @keyframes particle-float {
    0% {
      transform: translateY(100vh) scale(0);
      opacity: 0;
    }
    10% {
      opacity: var(--opacity, 0.3);
      transform: translateY(80vh) scale(1);
    }
    90% {
      opacity: var(--opacity, 0.3);
    }
    100% {
      transform: translateY(-20vh) scale(0.5);
      opacity: 0;
    }
  }

  /* ============================================
     FLOATING KANJI
     ============================================ */
  .kanji-container {
    position: absolute;
    inset: 0;
    pointer-events: none;
    overflow: hidden;
  }

  .floating-kanji {
    position: absolute;
    bottom: -100px;
    font-size: 4rem;
    font-weight: 100;
    color: rgba(139, 92, 246, 0.06);
    animation: kanji-rise linear infinite;
    font-family: 'Hiragino Kaku Gothic Pro', 'Yu Gothic', sans-serif;
  }

  @keyframes kanji-rise {
    0% {
      transform: translateY(0) rotate(0deg);
      opacity: 0;
    }
    5% {
      opacity: 0.06;
    }
    95% {
      opacity: 0.06;
    }
    100% {
      transform: translateY(-120vh) rotate(20deg);
      opacity: 0;
    }
  }

  /* ============================================
     BIMBO ORB
     ============================================ */
  .orb-container {
    position: absolute;
    top: 15%;
    right: 15%;
    width: 120px;
    height: 120px;
    pointer-events: none;
  }

  .orb-glow {
    position: absolute;
    inset: -40px;
    background: radial-gradient(circle, rgba(139, 92, 246, 0.3) 0%, transparent 70%);
    animation: orb-glow-pulse 3s ease-in-out infinite;
  }

  .orb-core {
    position: absolute;
    inset: 30px;
    background: radial-gradient(circle at 30% 30%, #c4b5fd 0%, #8b5cf6 50%, #6d28d9 100%);
    border-radius: 50%;
    box-shadow: 0 0 40px rgba(139, 92, 246, 0.5);
    animation: orb-float 6s ease-in-out infinite;
  }

  .orb-ring {
    position: absolute;
    inset: 20px;
    border: 1px solid rgba(139, 92, 246, 0.3);
    border-radius: 50%;
    animation: orb-ring-spin 20s linear infinite;
  }

  @keyframes orb-glow-pulse {
    0%, 100% { transform: scale(1); opacity: 0.5; }
    50% { transform: scale(1.2); opacity: 0.8; }
  }

  @keyframes orb-float {
    0%, 100% { transform: translateY(0) rotate(0deg); }
    50% { transform: translateY(-15px) rotate(5deg); }
  }

  @keyframes orb-ring-spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  /* ============================================
     CONTENT
     ============================================ */
  .content {
    position: relative;
    z-index: 10;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    padding: 20px;
    max-width: 800px;
    width: 100%;
  }

  /* ============================================
     TITLE
     ============================================ */
  .title-container {
    position: relative;
    margin-bottom: 16px;
  }

  .game-title {
    font-size: clamp(3rem, 12vw, 5.5rem);
    font-weight: 900;
    letter-spacing: -0.03em;
    margin: 0;
    line-height: 1;
    text-shadow: 0 0 60px rgba(139, 92, 246, 0.5);
  }

  .title-lang {
    color: #e2e8f0;
  }

  .title-hero {
    background: linear-gradient(135deg, #a78bfa 0%, #8b5cf6 50%, #6366f1 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .title-glow {
    position: absolute;
    inset: -20px;
    background: radial-gradient(ellipse at center, rgba(139, 92, 246, 0.2) 0%, transparent 70%);
    filter: blur(20px);
    z-index: -1;
    animation: title-glow-pulse 4s ease-in-out infinite;
  }

  @keyframes title-glow-pulse {
    0%, 100% { opacity: 0.5; }
    50% { opacity: 0.8; }
  }

  /* ============================================
     TAGLINE & DESCRIPTION
     ============================================ */
  .tagline {
    font-size: 1.4rem;
    font-weight: 600;
    color: #a78bfa;
    margin: 0 0 8px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }

  .description {
    font-size: 1.1rem;
    color: #94a3b8;
    margin: 0 0 48px;
    font-weight: 500;
  }

  /* ============================================
     MENU CONTAINER
     ============================================ */
  .menu-container {
    display: flex;
    gap: 32px;
    align-items: flex-start;
    width: 100%;
    max-width: 700px;
  }

  /* ============================================
     MENU OPTIONS
     ============================================ */
  .menu-options {
    display: flex;
    flex-direction: column;
    gap: 10px;
    flex: 1;
    max-width: 320px;
  }

  .menu-btn {
    display: flex;
    align-items: center;
    gap: 14px;
    width: 100%;
    padding: 16px 18px;
    border: none;
    border-radius: 14px;
    cursor: pointer;
    text-align: left;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
    /* Touch-friendly */
    touch-action: manipulation;
    -webkit-tap-highlight-color: transparent;
    min-height: 56px;
  }

  .menu-btn::before {
    content: '';
    position: absolute;
    inset: 0;
    opacity: 0;
    transition: opacity 0.2s ease;
  }

  .menu-btn:hover::before,
  .menu-btn.active::before {
    opacity: 1;
  }

  .menu-btn:hover,
  .menu-btn.active {
    transform: translateX(6px);
  }

  .menu-btn:active {
    transform: translateX(3px) scale(0.98);
    transition-duration: 0.1s;
  }

  /* Active/pressed visual feedback for touch */
  .menu-btn:active .btn-icon {
    transform: scale(0.95);
  }

  /* Primary Button */
  .menu-btn.primary {
    background: linear-gradient(135deg, rgba(139, 92, 246, 0.25) 0%, rgba(99, 102, 241, 0.25) 100%);
    border: 1px solid rgba(139, 92, 246, 0.4);
    box-shadow: 0 4px 20px rgba(139, 92, 246, 0.15);
  }

  .menu-btn.primary::before {
    background: linear-gradient(135deg, rgba(139, 92, 246, 0.35) 0%, rgba(99, 102, 241, 0.35) 100%);
  }

  .menu-btn.primary:hover,
  .menu-btn.primary.active {
    box-shadow: 0 6px 25px rgba(139, 92, 246, 0.3);
    border-color: rgba(139, 92, 246, 0.6);
  }

  /* Secondary Button */
  .menu-btn.secondary {
    background: rgba(59, 130, 246, 0.12);
    border: 1px solid rgba(59, 130, 246, 0.25);
  }

  .menu-btn.secondary::before {
    background: rgba(59, 130, 246, 0.2);
  }

  .menu-btn.secondary:hover,
  .menu-btn.secondary.active {
    border-color: rgba(59, 130, 246, 0.45);
  }

  /* Tertiary Button */
  .menu-btn.tertiary {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
  }

  .menu-btn.tertiary::before {
    background: rgba(255, 255, 255, 0.06);
  }

  .menu-btn.tertiary:hover,
  .menu-btn.tertiary.active {
    border-color: rgba(255, 255, 255, 0.15);
  }

  /* Compact Button (for secondary actions) */
  .menu-btn.compact {
    background: transparent;
    border: 1px solid rgba(255, 255, 255, 0.06);
    padding: 10px 14px;
    min-height: 48px;
  }

  .menu-btn.compact::before {
    background: rgba(255, 255, 255, 0.04);
  }

  .menu-btn.compact:hover,
  .menu-btn.compact.active {
    border-color: rgba(255, 255, 255, 0.12);
  }

  .menu-btn.compact .btn-label {
    font-size: 0.9rem;
    color: #94a3b8;
  }

  .menu-btn.compact:hover .btn-label,
  .menu-btn.compact.active .btn-label {
    color: #e2e8f0;
  }

  /* Menu Divider */
  .menu-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.08), transparent);
    margin: 6px 0;
  }

  /* Button Icon */
  .btn-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    background: rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    flex-shrink: 0;
    transition: all 0.2s ease;
  }

  .btn-icon svg {
    width: 20px;
    height: 20px;
    color: #cbd5e1;
  }

  .menu-btn.primary .btn-icon {
    background: rgba(139, 92, 246, 0.25);
  }

  .menu-btn.primary .btn-icon svg {
    color: #c4b5fd;
  }

  .menu-btn:hover .btn-icon,
  .menu-btn.active .btn-icon {
    transform: scale(1.05);
  }

  /* Small icon for compact buttons */
  .btn-icon.small {
    width: 32px;
    height: 32px;
    background: rgba(255, 255, 255, 0.05);
  }

  .btn-icon.small svg {
    width: 16px;
    height: 16px;
    color: #64748b;
  }

  .menu-btn:hover .btn-icon.small svg,
  .menu-btn.active .btn-icon.small svg {
    color: #94a3b8;
  }

  /* Button Text Container */
  .btn-text {
    display: flex;
    flex-direction: column;
    gap: 2px;
    flex: 1;
    min-width: 0;
  }

  /* Button Label */
  .btn-label {
    font-size: 1rem;
    font-weight: 700;
    color: #f1f5f9;
  }

  .menu-btn.primary .btn-label {
    color: #fff;
  }

  /* Button Subtitle - visible on mobile for quick context */
  .btn-subtitle {
    font-size: 0.8rem;
    font-weight: 500;
    color: #64748b;
    display: none;
  }

  /* Selected state (mobile tap-to-select) */
  .menu-btn.selected {
    transform: translateX(8px);
  }

  .menu-btn.selected::after {
    content: '';
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 3px;
    background: linear-gradient(180deg, #8b5cf6, #6366f1);
    border-radius: 0 2px 2px 0;
  }

  .menu-btn.selected .btn-arrow {
    opacity: 1;
    transform: translateX(0);
    color: #a78bfa;
  }

  /* Button Arrow */
  .btn-arrow {
    font-size: 1.3rem;
    color: #8b5cf6;
    opacity: 0;
    transform: translateX(-8px);
    transition: all 0.2s ease;
  }

  .menu-btn.primary:hover .btn-arrow,
  .menu-btn.primary.active .btn-arrow {
    opacity: 1;
    transform: translateX(0);
  }

  /* Button Badge */
  .btn-badge {
    font-size: 0.75rem;
    font-weight: 700;
    padding: 3px 8px;
    background: rgba(139, 92, 246, 0.2);
    color: #a78bfa;
    border-radius: 10px;
  }

  /* ============================================
     DESCRIPTION PANEL
     ============================================ */
  .description-panel {
    flex: 1;
    min-height: 160px;
    padding: 20px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.3s ease;
  }

  .description-panel.visible {
    background: rgba(139, 92, 246, 0.06);
    border-color: rgba(139, 92, 246, 0.15);
  }

  .desc-content {
    text-align: left;
  }

  .desc-title {
    font-size: 1.15rem;
    font-weight: 700;
    color: #f1f5f9;
    margin: 0 0 10px;
  }

  .desc-text {
    font-size: 0.95rem;
    color: #94a3b8;
    line-height: 1.5;
    margin: 0 0 12px;
  }

  .desc-extra {
    font-size: 0.8rem;
    font-weight: 600;
    color: #8b5cf6;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .desc-tap-hint {
    margin: 12px 0 0;
    font-size: 0.85rem;
    font-weight: 600;
    color: #a78bfa;
    animation: pulse-hint 1.5s ease-in-out infinite;
  }

  @keyframes pulse-hint {
    0%, 100% { opacity: 0.7; }
    50% { opacity: 1; }
  }

  .desc-placeholder {
    text-align: center;
  }

  .desc-placeholder p {
    margin: 0;
    font-size: 0.9rem;
    color: #475569;
    font-style: italic;
  }

  /* Show appropriate hint based on device */
  .mobile-hint {
    display: none;
  }

  .desktop-hint {
    display: block;
  }

  /* ============================================
     FOOTER
     ============================================ */
  .footer {
    position: absolute;
    bottom: 24px;
    left: 0;
    right: 0;
    text-align: center;
  }

  .version {
    margin: 0;
    font-size: 0.85rem;
    color: #475569;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
  }

  /* ============================================
     HOVER BACKDROP
     ============================================ */
  .hover-backdrop {
    position: absolute;
    inset: 0;
    pointer-events: none;
    z-index: 1;
  }

  .hover-backdrop.story {
    background: radial-gradient(ellipse at 50% 60%, rgba(139, 92, 246, 0.08) 0%, transparent 60%);
  }

  /* ============================================
     RESPONSIVE - MOBILE FIRST
     ============================================ */
  @media (max-width: 700px) {
    .menu-container {
      flex-direction: column;
      align-items: center;
      gap: 20px;
    }

    .menu-options {
      max-width: 100%;
      width: 100%;
    }

    /* Show subtitles on mobile for quick context */
    .btn-subtitle {
      display: block;
    }

    /* Mobile buttons need more padding for touch */
    .menu-btn {
      padding: 18px 20px;
      min-height: 64px;
    }

    .description-panel {
      width: 100%;
      min-height: 100px;
    }

    /* Show mobile hints, hide desktop hints */
    .mobile-hint {
      display: block;
    }

    .desktop-hint {
      display: none;
    }

    .orb-container {
      top: 8%;
      right: 8%;
      width: 80px;
      height: 80px;
    }

    .orb-core {
      inset: 20px;
    }

    .orb-ring {
      inset: 12px;
    }

    .floating-kanji {
      font-size: 2.5rem;
    }

    .description {
      margin-bottom: 36px;
    }

    /* Show arrow on all selected buttons on mobile */
    .menu-btn.selected .btn-arrow {
      display: inline;
    }

    /* Compact buttons on mobile */
    .menu-btn.compact {
      padding: 14px 16px;
      min-height: 52px;
    }

    .menu-divider {
      margin: 10px 0;
    }
  }

  /* Extra small screens - simplify even more */
  @media (max-width: 400px) {
    .content {
      padding: 16px;
    }

    .menu-btn {
      padding: 16px;
      gap: 12px;
    }

    .btn-icon {
      width: 36px;
      height: 36px;
    }

    .btn-icon svg {
      width: 18px;
      height: 18px;
    }

    .tagline {
      font-size: 1.2rem;
    }

    .description {
      font-size: 1rem;
    }
  }

  /* ============================================
     REDUCED MOTION
     ============================================ */
  @media (prefers-reduced-motion: reduce) {
    .bg-stars,
    .bg-nebula,
    .particle,
    .floating-kanji,
    .orb-glow,
    .orb-core,
    .orb-ring,
    .title-glow {
      animation: none;
    }

    .menu-btn,
    .menu-btn::before,
    .btn-icon,
    .btn-arrow {
      transition: none;
    }
  }

  /* ============================================
     START NEW MODAL
     ============================================ */
  .modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.8);
    backdrop-filter: blur(8px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    padding: 24px;
  }

  .modal-content {
    background: linear-gradient(135deg, rgba(30, 30, 50, 0.95) 0%, rgba(20, 20, 35, 0.98) 100%);
    border: 1px solid rgba(139, 92, 246, 0.3);
    border-radius: 20px;
    padding: 32px;
    max-width: 400px;
    width: 100%;
    box-shadow:
      0 20px 60px rgba(0, 0, 0, 0.5),
      0 0 40px rgba(139, 92, 246, 0.1);
  }

  .modal-title {
    margin: 0 0 16px;
    font-size: 1.5rem;
    font-weight: 700;
    color: #f1f5f9;
  }

  .modal-text {
    margin: 0 0 12px;
    font-size: 1rem;
    color: #94a3b8;
    line-height: 1.5;
  }

  .modal-warning {
    margin: 0 0 24px;
    font-size: 0.9rem;
    color: #64748b;
    font-style: italic;
  }

  .modal-actions {
    display: flex;
    gap: 12px;
    justify-content: flex-end;
  }

  .modal-btn {
    padding: 12px 24px;
    border-radius: 12px;
    font-size: 0.95rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
    border: none;
  }

  .modal-btn.cancel {
    background: rgba(255, 255, 255, 0.08);
    color: #94a3b8;
    border: 1px solid rgba(255, 255, 255, 0.1);
  }

  .modal-btn.cancel:hover {
    background: rgba(255, 255, 255, 0.12);
    color: #e2e8f0;
  }

  .modal-btn.confirm {
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.8) 0%, rgba(220, 38, 38, 0.8) 100%);
    color: #fff;
    border: 1px solid rgba(239, 68, 68, 0.5);
  }

  .modal-btn.confirm:hover {
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.9) 0%, rgba(220, 38, 38, 0.9) 100%);
    box-shadow: 0 4px 20px rgba(239, 68, 68, 0.3);
  }

  /* Start New button styling */
  .menu-btn.start-new {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.2);
  }

  .menu-btn.start-new::before {
    background: rgba(239, 68, 68, 0.15);
  }

  .menu-btn.start-new:hover,
  .menu-btn.start-new.active {
    border-color: rgba(239, 68, 68, 0.4);
  }

  .menu-btn.start-new .btn-icon {
    background: rgba(239, 68, 68, 0.2);
  }

  .menu-btn.start-new .btn-icon svg {
    color: #fca5a5;
  }

  /* Mobile modal */
  @media (max-width: 500px) {
    .modal-content {
      padding: 24px;
    }

    .modal-actions {
      flex-direction: column;
    }

    .modal-btn {
      width: 100%;
      text-align: center;
    }
  }
</style>
