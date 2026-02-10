<script>
  /**
   * AwakeningCutscene - Dramatic entry to the main story.
   *
   * Plays the awakening dialogue with:
   * - Dynamic background transitions (beach → samurai confrontation)
   * - Dramatic pacing between lines
   * - Cinematic aesthetic (warm tones, grounded)
   * - Auto-triggers time-freeze at end
   * - PC keyboard hints
   * - Auto TTS for Bimbo
   */
  import { createEventDispatcher, onMount, onDestroy, getContext } from 'svelte';
  import { fade, fly, scale } from 'svelte/transition';
  import { cubicOut, cubicIn } from 'svelte/easing';
  import { getTTS } from '$lib/api';
  import { masterVolume, playbackSpeed } from '$lib/audioStore.js';
  import { canGoBack, storyManager } from '$lib/storyManager.js';

  export let dialogue = null;
  export let isComplete = false;
  export let enableTTS = true;
  /** @type {{ id?: string, image_url?: string, mood?: string, effects?: string[], scene_description?: string } | null} */
  export let panel = null;

  const dispatch = createEventDispatcher();
  const aesthetic = getContext('aesthetic');

  // Device detection
  let isTouchDevice = false;
  let audioElement = null;
  let isPlayingTTS = false;

  // Fallback background images for different scenes (used when panel is not available)
  const fallbackBackgrounds = {
    beach_storm: 'https://images.unsplash.com/photo-1534274988757-a28bf1a57c17?w=1200&q=80',
    samurai_face: 'https://images.unsplash.com/photo-1590794056226-79ef3a8147e1?w=1200&q=80',
    time_frozen: 'https://images.unsplash.com/photo-1507400492013-162706c8c05e?w=1200&q=80',
  };

  // Current background URL - prefer panel.image_url if available
  let currentBgUrl = fallbackBackgrounds.beach_storm;
  let showLetterbox = false;
  let showTimeFreezeOverlay = false;
  let autoAdvanceTimer = null;

  // Determine background from panel or fallback to content-based detection
  $: {
    if (panel?.image_url) {
      // Use panel-provided image URL (1:1 line mapping)
      currentBgUrl = panel.image_url;

      // Determine effects from panel mood
      const mood = panel.mood?.toLowerCase() || '';
      const panelId = panel.id?.toLowerCase() || '';

      showTimeFreezeOverlay = panelId.includes('time_frozen') || panelId.includes('bimbo_orb_battlefield');
      showLetterbox = mood === 'dramatic' || mood === 'tense' || panelId.includes('samurai') || panelId.includes('blade');
    } else if (dialogue) {
      // Fallback: Switch backgrounds based on content
      const speaker = dialogue.speaker?.toLowerCase() || '';
      const text = dialogue.text || '';

      if (speaker === 'samurai' || text.includes('何者') || text.includes('答えろ')) {
        currentBgUrl = fallbackBackgrounds.samurai_face;
        showLetterbox = true;
        showTimeFreezeOverlay = false;
      } else if (text.includes('freeze') || text.includes('Bought you some time')) {
        currentBgUrl = fallbackBackgrounds.time_frozen;
        showTimeFreezeOverlay = true;
        showLetterbox = false;
      } else if (speaker === 'narration' && (text.includes('eyes open') || text.includes('beach'))) {
        currentBgUrl = fallbackBackgrounds.beach_storm;
        showLetterbox = false;
        showTimeFreezeOverlay = false;
      } else {
        showLetterbox = speaker === 'samurai';
      }
    }
  }

  // Speaker styling for cinematic mode
  $: speakerClass = (() => {
    if (!dialogue?.speaker) return '';
    switch (dialogue.speaker.toLowerCase()) {
      case 'bimbo': return 'speaker-bimbo';
      case 'player': return 'speaker-player';
      case 'narration': return 'speaker-narration';
      case 'samurai': return 'speaker-samurai';
      default: return 'speaker-npc';
    }
  })();

  // Get speaker display name
  $: speakerName = (() => {
    if (!dialogue?.speaker) return '';
    switch (dialogue.speaker.toLowerCase()) {
      case 'bimbo': return 'Bimbo';
      case 'player': return 'You';
      case 'narration': return '';
      case 'samurai': return 'Samurai';
      default: return dialogue.speaker;
    }
  })();

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

  function handleComplete() {
    if (autoAdvanceTimer) {
      clearTimeout(autoAdvanceTimer);
    }
    dispatch('complete');
  }

  // Check for completion
  $: if (isComplete) {
    // Give a moment before transitioning
    autoAdvanceTimer = setTimeout(handleComplete, 500);
  }

  // Auto-play TTS for Bimbo's lines
  $: if (dialogue && enableTTS) {
    playBimboTTS(dialogue);
  }

  async function playBimboTTS(dialogueLine) {
    if (!dialogueLine || dialogueLine.speaker?.toLowerCase() !== 'bimbo') {
      return;
    }

    if (isPlayingTTS) return;

    try {
      isPlayingTTS = true;
      const response = await getTTS({
        text: dialogueLine.text,
        role: 'bimbo',
        sentiment: dialogueLine.sentiment || 'encouraging',
      });

      if (response.url && !response.error) {
        if (audioElement) {
          audioElement.pause();
          audioElement = null;
        }

        audioElement = new Audio(response.url);
        audioElement.playbackRate = $playbackSpeed;
        audioElement.volume = $masterVolume;
        audioElement.onended = () => { isPlayingTTS = false; };
        audioElement.onerror = () => { isPlayingTTS = false; };

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

  // Continue hint text
  $: continueHint = (() => {
    if (isComplete) return 'Continue';
    if (isTouchDevice) return 'Tap to continue';
    return 'Press SPACE to continue';
  })();

  onMount(() => {
    isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;

    return () => {
      if (autoAdvanceTimer) {
        clearTimeout(autoAdvanceTimer);
      }
    };
  });

  onDestroy(() => {
    if (audioElement) {
      audioElement.pause();
      audioElement = null;
    }
  });
</script>

<svelte:window on:keydown={handleKeydown} />

<!-- svelte-ignore a11y-click-events-have-key-events -->
<!-- svelte-ignore a11y-no-static-element-interactions -->
<div class="awakening-cutscene" on:click={handleClick}>
  <!-- Dynamic background - uses panel image or fallback -->
  <div class="background-layer">
    {#key currentBgUrl}
      <div
        class="background-image"
        style="background-image: url({currentBgUrl})"
        in:fade={{ duration: 800 }}
      ></div>
    {/key}

    <!-- Cinematic overlays -->
    <div class="cinematic-overlay"></div>

    {#if showTimeFreezeOverlay}
      <div class="time-freeze-overlay" in:fade={{ duration: 500 }}></div>
      <div class="frozen-particles" in:fade={{ duration: 800, delay: 200 }}>
        {#each Array(15) as _, i}
          <div
            class="frozen-particle"
            style="
              left: {10 + Math.random() * 80}%;
              top: {10 + Math.random() * 80}%;
              animation-delay: {i * 0.1}s;
            "
          ></div>
        {/each}
      </div>
    {/if}
  </div>

  <!-- Letterbox bars for dramatic moments -->
  <div class="letterbox" class:active={showLetterbox}>
    <div class="letterbox-bar top"></div>
    <div class="letterbox-bar bottom"></div>
  </div>

  <!-- Dialogue content -->
  <div class="dialogue-area">
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
        {#if dialogue}
          {#key dialogue.text}
            <div
              class="dialogue-box {speakerClass}"
              in:fly={{ y: 30, duration: 400, easing: cubicOut }}
            >
              {#if speakerName}
                <span class="speaker-name">{speakerName}</span>
              {/if}
              <p class="dialogue-text">{dialogue.text}</p>
              {#if dialogue.sub}
                <p class="dialogue-sub">{dialogue.sub}</p>
              {/if}
            </div>
          {/key}
        {/if}
      </div>
    </div>

    <div class="continue-hint" class:complete={isComplete}>
      {continueHint}
    </div>
  </div>

  <!-- Bimbo orb (smaller, more subtle in cinematic mode) -->
  {#if dialogue?.speaker?.toLowerCase() === 'bimbo'}
    <div class="bimbo-orb-mini" in:scale={{ duration: 300 }}>
      <div class="orb-glow"></div>
      <div class="orb-core"></div>
    </div>
  {/if}

  <!-- Skip button -->
  <button class="skip-btn" on:click|stopPropagation={() => dispatch('skip')}>
    Skip
  </button>
</div>

<style>
  .awakening-cutscene {
    position: fixed;
    inset: 0;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    cursor: pointer;
    z-index: 100;
    overflow: hidden;
  }

  /* Background layers */
  .background-layer {
    position: absolute;
    inset: 0;
  }

  .background-image {
    position: absolute;
    inset: 0;
    background-size: cover;
    background-position: center;
    filter: brightness(0.5) saturate(0.8);
  }

  .cinematic-overlay {
    position: absolute;
    inset: 0;
    background:
      linear-gradient(to bottom, rgba(26, 21, 21, 0.4) 0%, transparent 30%),
      linear-gradient(to top, rgba(26, 21, 21, 0.9) 0%, transparent 50%);
  }

  /* Time freeze effect */
  .time-freeze-overlay {
    position: absolute;
    inset: 0;
    background: rgba(139, 92, 246, 0.15);
    mix-blend-mode: overlay;
  }

  .frozen-particles {
    position: absolute;
    inset: 0;
  }

  .frozen-particle {
    position: absolute;
    width: 4px;
    height: 4px;
    background: rgba(196, 181, 253, 0.7);
    border-radius: 50%;
    box-shadow: 0 0 8px rgba(139, 92, 246, 0.9);
    animation: particle-float 3s ease-in-out infinite alternate;
  }

  @keyframes particle-float {
    0% { transform: translateY(0) scale(1); opacity: 0.7; }
    100% { transform: translateY(-10px) scale(0.8); opacity: 1; }
  }

  /* Letterbox */
  .letterbox {
    position: absolute;
    inset: 0;
    pointer-events: none;
    z-index: 10;
  }

  .letterbox-bar {
    position: absolute;
    left: 0;
    right: 0;
    height: 0;
    background: #000;
    transition: height 0.6s ease;
  }

  .letterbox-bar.top { top: 0; }
  .letterbox-bar.bottom { bottom: 0; }

  .letterbox.active .letterbox-bar {
    height: 8vh;
  }

  /* Dialogue area */
  .dialogue-area {
    position: relative;
    z-index: 20;
    width: 100%;
    max-width: 500px;
    padding: 24px;
    padding-bottom: max(24px, env(safe-area-inset-bottom));
    margin: 0 auto;
  }

  .dialogue-box {
    background: rgba(26, 21, 21, 0.95);
    backdrop-filter: blur(12px);
    border-radius: 16px;
    padding: 20px 24px;
    border: 1px solid rgba(254, 243, 199, 0.15);
    margin-bottom: 16px;
  }

  /* Speaker styles - Cinematic mode */
  .speaker-bimbo {
    background: rgba(251, 191, 36, 0.12);
    border-color: rgba(251, 191, 36, 0.25);
  }

  .speaker-player {
    background: rgba(34, 197, 94, 0.12);
    border-color: rgba(34, 197, 94, 0.25);
  }

  .speaker-narration {
    background: transparent;
    border: none;
    text-align: center;
  }

  .speaker-samurai {
    background: rgba(220, 38, 38, 0.15);
    border-color: rgba(220, 38, 38, 0.4);
    box-shadow: 0 0 20px rgba(220, 38, 38, 0.2);
  }

  .speaker-npc {
    background: rgba(254, 243, 199, 0.1);
    border-color: rgba(254, 243, 199, 0.2);
  }

  .speaker-name {
    display: block;
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 8px;
  }

  .speaker-bimbo .speaker-name {
    color: #fde68a;
  }

  .speaker-player .speaker-name {
    color: #86efac;
  }

  .speaker-samurai .speaker-name {
    color: #fca5a5;
  }

  .speaker-npc .speaker-name {
    color: #fcd34d;
  }

  .dialogue-text {
    margin: 0;
    font-size: 1.1rem;
    line-height: 1.6;
    color: #fef3c7;
  }

  .speaker-narration .dialogue-text {
    font-style: italic;
    color: rgba(254, 243, 199, 0.8);
  }

  .speaker-samurai .dialogue-text {
    font-weight: 600;
  }

  .dialogue-sub {
    margin: 8px 0 0;
    font-size: 0.9rem;
    color: rgba(254, 243, 199, 0.5);
    font-style: italic;
  }

  .continue-hint {
    text-align: center;
    font-size: 0.85rem;
    color: rgba(254, 243, 199, 0.4);
    animation: hint-pulse 2s ease-in-out infinite;
  }

  .continue-hint.complete {
    color: rgba(251, 191, 36, 0.8);
  }

  @keyframes hint-pulse {
    0%, 100% { opacity: 0.4; }
    50% { opacity: 0.7; }
  }

  /* Bimbo orb - smaller for cinematic */
  .bimbo-orb-mini {
    position: absolute;
    bottom: 280px;
    left: 24px;
    width: 50px;
    height: 50px;
    z-index: 30;
  }

  .bimbo-orb-mini .orb-glow {
    position: absolute;
    inset: -12px;
    background: radial-gradient(
      circle,
      rgba(251, 191, 36, 0.4) 0%,
      transparent 70%
    );
    animation: orb-pulse 2s ease-in-out infinite;
  }

  .bimbo-orb-mini .orb-core {
    position: absolute;
    inset: 8px;
    background: radial-gradient(
      circle at 30% 30%,
      #fde68a 0%,
      #fbbf24 50%,
      #d97706 100%
    );
    border-radius: 50%;
    box-shadow: 0 0 15px rgba(251, 191, 36, 0.5);
  }

  @keyframes orb-pulse {
    0%, 100% { transform: scale(1); opacity: 0.7; }
    50% { transform: scale(1.1); opacity: 1; }
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
    background: rgba(0, 0, 0, 0.5);
    border: 1px solid rgba(254, 243, 199, 0.2);
    color: rgba(254, 243, 199, 0.6);
    border-radius: 50%;
    cursor: pointer;
    transition: all 0.2s;
    margin-top: 8px;
  }

  .back-btn:hover {
    background: rgba(0, 0, 0, 0.7);
    color: rgba(254, 243, 199, 0.9);
    border-color: rgba(254, 243, 199, 0.4);
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
    background: rgba(0, 0, 0, 0.5);
    border: 1px solid rgba(254, 243, 199, 0.2);
    color: rgba(254, 243, 199, 0.6);
    padding: 8px 16px;
    border-radius: 20px;
    font-size: 0.85rem;
    cursor: pointer;
    z-index: 100;
    transition: all 0.2s;
  }

  .skip-btn:hover {
    background: rgba(0, 0, 0, 0.7);
    color: rgba(254, 243, 199, 0.9);
    border-color: rgba(254, 243, 199, 0.4);
  }

  /* Mobile adjustments */
  @media (max-width: 500px) {
    .dialogue-area {
      padding: 16px;
    }

    .bimbo-orb-mini {
      width: 40px;
      height: 40px;
      left: 16px;
      bottom: 240px;
    }
  }

  /* Reduced motion */
  @media (prefers-reduced-motion: reduce) {
    .frozen-particle,
    .orb-glow,
    .continue-hint {
      animation: none;
    }

    .letterbox-bar {
      transition: none;
    }
  }
</style>
