<script>
  /**
   * DropSequence - Dramatic time travel transition.
   *
   * Visual sequence: dialogue → white flash → vortex → falling → landing
   *
   * Features:
   * - Respects prefers-reduced-motion
   * - Optimized particle count for mobile
   * - Smooth aesthetic transition point
   */
  import { onMount, createEventDispatcher } from 'svelte';
  import { fade, fly, scale } from 'svelte/transition';
  import { cubicOut, cubicIn } from 'svelte/easing';

  export let dialogue = null;

  const dispatch = createEventDispatcher();

  // Sequence phases
  let phase = 'dialogue'; // dialogue → flash → vortex → falling → landing
  let showDialogue = true;
  let showVortex = false;
  let showFlash = false;
  let showFalling = false;

  // Accessibility and performance
  let prefersReducedMotion = false;
  let isMobile = false;

  // Particle count based on device capability
  $: particleCount = isMobile ? 12 : 20;

  onMount(() => {
    // Check for reduced motion preference
    const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    prefersReducedMotion = motionQuery.matches;
    motionQuery.addEventListener('change', (e) => {
      prefersReducedMotion = e.matches;
    });

    // Check if mobile (for performance optimization)
    isMobile = window.innerWidth < 768 || 'ontouchstart' in window;

    // Start the sequence
    setTimeout(startSequence, 500);
  });

  function startSequence() {
    // If reduced motion, skip animations and complete quickly
    if (prefersReducedMotion) {
      showDialogue = true;
      setTimeout(() => {
        showDialogue = false;
        phase = 'landing';
        dispatch('complete');
      }, 1500);
      return;
    }

    // Phase 1: Show dialogue briefly
    showDialogue = true;

    setTimeout(() => {
      // Phase 2: Flash
      showDialogue = false;
      showFlash = true;
      phase = 'flash';

      setTimeout(() => {
        showFlash = false;
        showVortex = true;
        phase = 'vortex';

        setTimeout(() => {
          // Phase 3: Falling
          showFalling = true;
          phase = 'falling';

          setTimeout(() => {
            // Phase 4: Complete
            phase = 'landing';
            dispatch('complete');
          }, 2000);
        }, 1500);
      }, 300);
    }, 2000);
  }

  function handleSkip() {
    dispatch('complete');
  }
</script>

<div class="drop-sequence" class:vortex-bg={showVortex || showFalling}>
  <!-- Dialogue phase -->
  {#if showDialogue && dialogue}
    <div class="drop-dialogue" transition:fade={{ duration: 300 }}>
      <div class="orb-mini">
        <div class="orb-glow"></div>
        <div class="orb-core"></div>
      </div>
      <div class="drop-text">
        <p>{dialogue.text}</p>
      </div>
    </div>
  {/if}

  <!-- White flash -->
  {#if showFlash}
    <div
      class="flash-overlay"
      in:fade={{ duration: 100 }}
      out:fade={{ duration: 200 }}
    ></div>
  {/if}

  <!-- Vortex effect -->
  {#if showVortex}
    <div class="vortex-container" in:scale={{ duration: 500, easing: cubicOut }}>
      <div class="vortex-ring ring-1"></div>
      <div class="vortex-ring ring-2"></div>
      <div class="vortex-ring ring-3"></div>
      <div class="vortex-ring ring-4"></div>
      <div class="vortex-center"></div>
    </div>
  {/if}

  <!-- Falling effect -->
  {#if showFalling}
    <div class="falling-container" in:fade={{ duration: 300 }}>
      <div class="speed-lines">
        {#each Array(particleCount) as _, i}
          <div
            class="speed-line"
            style="
              --delay: {i * 0.05}s;
              --x: {Math.random() * 100}%;
              --length: {50 + Math.random() * 100}px;
            "
          ></div>
        {/each}
      </div>
      <div class="falling-text" in:fly={{ y: -50, duration: 500, delay: 500 }}>
        <p>Dropping in...</p>
      </div>
    </div>
  {/if}

  <!-- Skip button -->
  <button class="skip-btn" on:click={handleSkip}>
    Skip
  </button>
</div>

<style>
  .drop-sequence {
    position: fixed;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #0a0a1a 0%, #1a1a2e 50%, #16213e 100%);
    transition: background 0.5s ease;
    z-index: 200;
    overflow: hidden;
  }

  .vortex-bg {
    background: radial-gradient(ellipse at center, #2d1b4e 0%, #0a0a1a 70%);
  }

  /* Dialogue */
  .drop-dialogue {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 24px;
    padding: 24px;
  }

  .orb-mini {
    position: relative;
    width: 60px;
    height: 60px;
  }

  .orb-mini .orb-glow {
    position: absolute;
    inset: -15px;
    background: radial-gradient(
      circle,
      rgba(139, 92, 246, 0.4) 0%,
      transparent 70%
    );
    animation: orb-pulse 2s ease-in-out infinite;
  }

  .orb-mini .orb-core {
    position: absolute;
    inset: 8px;
    background: radial-gradient(
      circle at 30% 30%,
      #c4b5fd 0%,
      #8b5cf6 50%,
      #6d28d9 100%
    );
    border-radius: 50%;
    box-shadow: 0 0 20px rgba(139, 92, 246, 0.6);
  }

  @keyframes orb-pulse {
    0%, 100% { transform: scale(1); opacity: 0.8; }
    50% { transform: scale(1.1); opacity: 1; }
  }

  .drop-text {
    text-align: center;
    color: #e2e8f0;
    font-size: 1.2rem;
    max-width: 300px;
  }

  /* Flash */
  .flash-overlay {
    position: absolute;
    inset: 0;
    background: white;
    z-index: 10;
  }

  /* Vortex */
  .vortex-container {
    position: relative;
    width: 300px;
    height: 300px;
  }

  .vortex-ring {
    position: absolute;
    inset: 0;
    border: 2px solid rgba(139, 92, 246, 0.3);
    border-radius: 50%;
    animation: vortex-spin 3s linear infinite;
  }

  .ring-1 {
    inset: 20%;
    animation-duration: 2s;
    border-color: rgba(139, 92, 246, 0.6);
  }

  .ring-2 {
    inset: 30%;
    animation-duration: 2.5s;
    animation-direction: reverse;
  }

  .ring-3 {
    inset: 40%;
    animation-duration: 3s;
  }

  .ring-4 {
    inset: 10%;
    animation-duration: 4s;
    animation-direction: reverse;
    border-color: rgba(139, 92, 246, 0.2);
  }

  .vortex-center {
    position: absolute;
    inset: 45%;
    background: radial-gradient(circle, #8b5cf6 0%, transparent 70%);
    border-radius: 50%;
    animation: center-pulse 1s ease-in-out infinite;
  }

  @keyframes vortex-spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  @keyframes center-pulse {
    0%, 100% { transform: scale(1); opacity: 0.8; }
    50% { transform: scale(1.5); opacity: 1; }
  }

  /* Falling */
  .falling-container {
    position: relative;
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .speed-lines {
    position: absolute;
    inset: 0;
    overflow: hidden;
  }

  .speed-line {
    position: absolute;
    left: var(--x);
    top: -100px;
    width: 2px;
    height: var(--length);
    background: linear-gradient(
      to bottom,
      transparent,
      rgba(139, 92, 246, 0.6),
      transparent
    );
    animation: speed-fall 0.5s linear infinite;
    animation-delay: var(--delay);
  }

  @keyframes speed-fall {
    from {
      transform: translateY(0);
      opacity: 0;
    }
    50% {
      opacity: 1;
    }
    to {
      transform: translateY(calc(100vh + 200px));
      opacity: 0;
    }
  }

  .falling-text {
    position: relative;
    z-index: 10;
    text-align: center;
    color: #e2e8f0;
    font-size: 1.5rem;
    font-weight: 600;
    text-shadow: 0 0 20px rgba(139, 92, 246, 0.8);
  }

  /* Skip button */
  .skip-btn {
    position: absolute;
    top: 16px;
    right: 16px;
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
    color: rgba(255, 255, 255, 0.5);
    padding: 8px 16px;
    border-radius: 20px;
    font-size: 0.85rem;
    cursor: pointer;
    z-index: 100;
    transition: all 0.2s;
  }

  .skip-btn:hover {
    background: rgba(255, 255, 255, 0.2);
    color: rgba(255, 255, 255, 0.8);
  }

  /* Mobile optimizations */
  @media (max-width: 768px) {
    .vortex-container {
      width: 200px;
      height: 200px;
    }

    .falling-text p {
      font-size: 1.2rem;
    }

    .speed-line {
      animation-duration: 0.4s;
    }
  }

  /* Reduced motion */
  @media (prefers-reduced-motion: reduce) {
    .orb-glow,
    .vortex-ring,
    .vortex-center,
    .speed-line {
      animation: none;
    }

    .flash-overlay {
      opacity: 0.5;
    }

    .drop-sequence {
      transition: none;
    }
  }
</style>
