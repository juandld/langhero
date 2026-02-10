<script>
  /**
   * DialogueOverlay - Full-screen dialogue display for narrative moments.
   *
   * Used during intro, transitions, and story intros.
   * Adapts styling based on aesthetic context (holographic/cinematic).
   * Features:
   * - PC keyboard hints (spacebar)
   * - Auto TTS for Bimbo's voice
   */
  import { createEventDispatcher, getContext, onMount, onDestroy } from 'svelte';
  import { fade, fly } from 'svelte/transition';
  import { STORY_STATES, canGoBack, storyManager } from '$lib/storyManager.js';
  import { getTTS } from '$lib/api';
  import { masterVolume, playbackSpeed } from '$lib/audioStore.js';

  export let line = null;
  export let isComplete = false;
  export let state = STORY_STATES.INTRO;
  export let enableTTS = true;

  const dispatch = createEventDispatcher();

  // Get aesthetic from context (defaults to holographic)
  const aestheticStore = getContext('aesthetic');
  $: aesthetic = $aestheticStore || 'holographic';

  // Device detection
  let isTouchDevice = false;
  let audioElement = null;
  let isPlayingTTS = false;

  onMount(() => {
    isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
  });

  // Auto-play TTS for Bimbo's lines
  $: if (line && enableTTS) {
    playBimboTTS(line);
  }

  async function playBimboTTS(dialogueLine) {
    if (!dialogueLine || dialogueLine.speaker?.toLowerCase() !== 'bimbo') {
      return;
    }

    // Don't play if already playing
    if (isPlayingTTS) return;

    try {
      isPlayingTTS = true;
      const response = await getTTS({
        text: dialogueLine.text,
        role: 'bimbo',
        sentiment: dialogueLine.sentiment || 'friendly',
      });

      if (response.url && !response.error) {
        // Stop any currently playing audio
        if (audioElement) {
          audioElement.pause();
          audioElement = null;
        }

        audioElement = new Audio(response.url);
        audioElement.playbackRate = $playbackSpeed;
        audioElement.volume = $masterVolume;
        audioElement.onended = () => {
          isPlayingTTS = false;
        };
        audioElement.onerror = () => {
          isPlayingTTS = false;
        };

        // Subscribe to volume and speed changes while playing
        const unsubVolume = masterVolume.subscribe((vol) => {
          if (audioElement) audioElement.volume = vol;
        });
        const unsubSpeed = playbackSpeed.subscribe((spd) => {
          if (audioElement) audioElement.playbackRate = spd;
        });
        const originalOnended = audioElement.onended;
        audioElement.onended = (e) => {
          unsubVolume();
          unsubSpeed();
          if (originalOnended) originalOnended(e);
        };

        await audioElement.play();
      } else {
        isPlayingTTS = false;
      }
    } catch (e) {
      console.warn('TTS playback failed:', e);
      isPlayingTTS = false;
    }
  }

  onDestroy(() => {
    if (audioElement) {
      audioElement.pause();
      audioElement = null;
    }
  });

  function handleClick() {
    dispatch('advance');
  }

  function handleKeydown(e) {
    if (e.key === ' ' || e.key === 'Enter') {
      e.preventDefault();
      dispatch('advance');
    } else if (e.key === 'Escape') {
      dispatch('skip');
    } else if (e.key === 'Backspace' || e.key === 'ArrowLeft') {
      e.preventDefault();
      handleBack();
    }
  }

  function handleBack() {
    if ($canGoBack) {
      storyManager.goBackDialogue();
    }
  }

  // Speaker styling
  $: speakerClass = (() => {
    if (!line?.speaker) return '';
    switch (line.speaker) {
      case 'bimbo': return 'speaker-bimbo';
      case 'player': return 'speaker-player';
      case 'narration': return 'speaker-narration';
      default: return 'speaker-npc';
    }
  })();

  // Get speaker display name
  $: speakerName = (() => {
    if (!line?.speaker) return '';
    switch (line.speaker) {
      case 'bimbo': return 'Bimbo';
      case 'player': return 'You';
      case 'narration': return '';
      default: return line.speaker;
    }
  })();

  // State-specific messaging - show keyboard hint on PC
  $: continueText = (() => {
    if (isComplete) return 'Continue';
    if (isTouchDevice) return 'Tap to continue';
    return 'Press SPACE to continue';
  })();
</script>

<svelte:window on:keydown={handleKeydown} />

<!-- svelte-ignore a11y-click-events-have-key-events -->
<!-- svelte-ignore a11y-no-static-element-interactions -->
<div
  class="dialogue-overlay"
  class:holographic={aesthetic === 'holographic'}
  class:cinematic={aesthetic === 'cinematic'}
  on:click={handleClick}
  transition:fade={{ duration: 300 }}
>
  <!-- Background gradient overlay -->
  <div class="bg-gradient"></div>

  <!-- Bimbo orb (visible for bimbo dialogue) -->
  {#if line?.speaker === 'bimbo'}
    <div class="bimbo-orb" in:fade={{ duration: 400 }}>
      <div class="orb-glow"></div>
      <div class="orb-core"></div>
    </div>
  {/if}

  <!-- Dialogue content -->
  <div class="dialogue-content">
    <div class="dialogue-row">
      {#if $canGoBack}
        <button class="back-btn" on:click|stopPropagation={handleBack} aria-label="Go back">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </button>
      {:else}
        <div class="back-spacer"></div>
      {/if}

      <div class="dialogue-box-wrapper">
        {#if line}
          {#key line.text}
            <div class="dialogue-box {speakerClass}" in:fly={{ y: 20, duration: 300 }}>
              {#if speakerName}
                <span class="speaker-name">{speakerName}</span>
              {/if}
              <p class="dialogue-text">{line.text}</p>
              {#if line.sub}
                <p class="dialogue-sub">{line.sub}</p>
              {/if}
            </div>
          {/key}
        {/if}
      </div>
    </div>

    <div class="continue-hint" class:complete={isComplete}>
      {continueText}
    </div>
  </div>

  <!-- Skip button -->
  <button class="skip-btn" on:click|stopPropagation={() => dispatch('skip')}>
    Skip
  </button>
</div>

<style>
  .dialogue-overlay {
    position: fixed;
    inset: 0;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    align-items: center;
    cursor: pointer;
    z-index: 100;
  }

  /* ============================================
     HOLOGRAPHIC MODE (Tutorial/Future)
     ============================================ */
  .dialogue-overlay.holographic .bg-gradient {
    background: radial-gradient(
      ellipse at center bottom,
      rgba(99, 102, 241, 0.15) 0%,
      transparent 50%
    );
  }

  .dialogue-overlay.holographic .dialogue-box {
    background: rgba(10, 10, 26, 0.9);
    border: 1px solid rgba(139, 92, 246, 0.3);
    box-shadow: 0 0 20px rgba(139, 92, 246, 0.15), 0 0 40px rgba(6, 182, 212, 0.05);
  }

  .dialogue-overlay.holographic .orb-glow {
    background: radial-gradient(circle, rgba(139, 92, 246, 0.5) 0%, transparent 70%);
  }

  .dialogue-overlay.holographic .orb-core {
    background: radial-gradient(circle at 30% 30%, #c4b5fd 0%, #8b5cf6 50%, #6d28d9 100%);
    box-shadow: 0 0 20px rgba(139, 92, 246, 0.6), inset 0 0 20px rgba(255, 255, 255, 0.2);
  }

  .dialogue-overlay.holographic .dialogue-text {
    color: #f0f0ff;
  }

  .dialogue-overlay.holographic .continue-hint.complete {
    color: rgba(139, 92, 246, 0.8);
  }

  /* Scan-line text effect for holographic */
  .dialogue-overlay.holographic .dialogue-text::after {
    content: '';
    position: absolute;
    inset: 0;
    background: repeating-linear-gradient(
      0deg,
      transparent,
      transparent 2px,
      rgba(139, 92, 246, 0.03) 2px,
      rgba(139, 92, 246, 0.03) 4px
    );
    pointer-events: none;
    opacity: 0.5;
  }

  /* ============================================
     CINEMATIC MODE (Main Story/Past)
     ============================================ */
  .dialogue-overlay.cinematic .bg-gradient {
    background: radial-gradient(
      ellipse at center bottom,
      rgba(220, 38, 38, 0.08) 0%,
      transparent 50%
    );
  }

  .dialogue-overlay.cinematic .dialogue-box {
    background: rgba(26, 21, 21, 0.95);
    border: 1px solid rgba(254, 243, 199, 0.15);
    box-shadow: none;
  }

  .dialogue-overlay.cinematic .orb-glow {
    background: radial-gradient(circle, rgba(251, 191, 36, 0.4) 0%, transparent 70%);
  }

  .dialogue-overlay.cinematic .orb-core {
    background: radial-gradient(circle at 30% 30%, #fde68a 0%, #fbbf24 50%, #d97706 100%);
    box-shadow: 0 0 15px rgba(251, 191, 36, 0.5);
  }

  .dialogue-overlay.cinematic .dialogue-text {
    color: #fef3c7;
  }

  .dialogue-overlay.cinematic .continue-hint.complete {
    color: rgba(251, 191, 36, 0.8);
  }

  .dialogue-overlay.cinematic .speaker-bimbo .speaker-name {
    color: #fde68a;
  }

  /* ============================================
     SHARED STYLES
     ============================================ */
  .bg-gradient {
    position: absolute;
    inset: 0;
    pointer-events: none;
  }

  /* Bimbo orb */
  .bimbo-orb {
    position: absolute;
    bottom: 280px;
    left: 50%;
    transform: translateX(-50%);
    width: 80px;
    height: 80px;
  }

  .orb-glow {
    position: absolute;
    inset: -20px;
    animation: orb-pulse 2s ease-in-out infinite;
  }

  .orb-core {
    position: absolute;
    inset: 10px;
    border-radius: 50%;
  }

  @keyframes orb-pulse {
    0%, 100% {
      transform: scale(1);
      opacity: 0.8;
    }
    50% {
      transform: scale(1.1);
      opacity: 1;
    }
  }

  /* Dialogue content */
  .dialogue-content {
    position: relative;
    width: 100%;
    max-width: 500px;
    padding: 24px;
    padding-bottom: max(24px, env(safe-area-inset-bottom));
  }

  .dialogue-box {
    position: relative;
    backdrop-filter: blur(12px);
    border-radius: 16px;
    padding: 20px 24px;
    margin-bottom: 16px;
    overflow: hidden;
  }

  .speaker-bimbo {
    background: rgba(99, 102, 241, 0.15);
    border-color: rgba(139, 92, 246, 0.3);
  }

  .speaker-player {
    background: rgba(34, 197, 94, 0.12);
    border-color: rgba(34, 197, 94, 0.3);
  }

  .speaker-narration {
    background: transparent;
    border: none;
    text-align: center;
  }

  .speaker-npc {
    background: rgba(251, 191, 36, 0.12);
    border-color: rgba(251, 191, 36, 0.3);
  }

  .speaker-name {
    display: block;
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: rgba(255, 255, 255, 0.5);
    margin-bottom: 8px;
  }

  .speaker-bimbo .speaker-name {
    color: #c4b5fd;
  }

  .speaker-player .speaker-name {
    color: #86efac;
  }

  .speaker-npc .speaker-name {
    color: #fcd34d;
  }

  .dialogue-text {
    margin: 0;
    font-size: 1.1rem;
    line-height: 1.6;
  }

  .speaker-narration .dialogue-text {
    font-style: italic;
    opacity: 0.85;
  }

  .dialogue-sub {
    margin: 8px 0 0;
    font-size: 0.9rem;
    color: rgba(255, 255, 255, 0.5);
    font-style: italic;
  }

  .continue-hint {
    text-align: center;
    font-size: 0.85rem;
    color: rgba(255, 255, 255, 0.4);
    animation: hint-pulse 2s ease-in-out infinite;
  }

  @keyframes hint-pulse {
    0%, 100% { opacity: 0.4; }
    50% { opacity: 0.7; }
  }

  /* Dialogue row with back button */
  .dialogue-row {
    display: flex;
    align-items: flex-start;
    gap: 12px;
  }

  .dialogue-box-wrapper {
    flex: 1;
    min-width: 0;
  }

  .back-btn {
    flex-shrink: 0;
    width: 36px;
    height: 36px;
    padding: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
    color: rgba(255, 255, 255, 0.5);
    border-radius: 50%;
    cursor: pointer;
    transition: all 0.2s;
    margin-top: 8px;
  }

  .back-btn:hover {
    background: rgba(255, 255, 255, 0.2);
    color: rgba(255, 255, 255, 0.8);
    transform: scale(1.05);
  }

  .back-btn:active {
    transform: scale(0.95);
  }

  .back-btn svg {
    width: 18px;
    height: 18px;
  }

  .back-spacer {
    width: 36px;
    flex-shrink: 0;
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
    transition: all 0.2s;
  }

  .skip-btn:hover {
    background: rgba(255, 255, 255, 0.2);
    color: rgba(255, 255, 255, 0.8);
  }

  /* Reduced motion */
  @media (prefers-reduced-motion: reduce) {
    .orb-glow,
    .continue-hint {
      animation: none;
    }
  }
</style>
