<script>
  import { createEventDispatcher, onMount, onDestroy } from 'svelte';
  import { fade, fly } from 'svelte/transition';
  import MangaPanel from './MangaPanel.svelte';

  export let panels = [];
  export let autoAdvance = false;
  export let showControls = true;
  export let currentIndex = 0;

  const dispatch = createEventDispatcher();

  let timer = null;

  $: currentPanel = panels[currentIndex] || null;
  $: isFirst = currentIndex === 0;
  $: isLast = currentIndex >= panels.length - 1;
  $: progress = panels.length > 0 ? ((currentIndex + 1) / panels.length) * 100 : 0;

  function next() {
    if (currentIndex < panels.length - 1) {
      currentIndex++;
      dispatch('change', { index: currentIndex, panel: panels[currentIndex] });
    } else {
      dispatch('complete');
    }
  }

  function previous() {
    if (currentIndex > 0) {
      currentIndex--;
      dispatch('change', { index: currentIndex, panel: panels[currentIndex] });
    }
  }

  function goTo(index) {
    if (index >= 0 && index < panels.length) {
      currentIndex = index;
      dispatch('change', { index: currentIndex, panel: panels[currentIndex] });
    }
  }

  function handlePanelClick() {
    next();
  }

  function handleKeydown(e) {
    if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'Enter') {
      e.preventDefault();
      next();
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      previous();
    } else if (e.key === 'Escape') {
      dispatch('skip');
    }
  }

  function startAutoAdvance() {
    stopAutoAdvance();
    if (autoAdvance && currentPanel) {
      const duration = currentPanel.duration_ms || 3000;
      timer = setTimeout(() => {
        next();
      }, duration);
    }
  }

  function stopAutoAdvance() {
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
  }

  // Auto-advance when panel changes
  $: if (autoAdvance && currentPanel) {
    startAutoAdvance();
  }

  onMount(() => {
    if (autoAdvance) startAutoAdvance();
  });

  onDestroy(() => {
    stopAutoAdvance();
  });
</script>

<svelte:window on:keydown={handleKeydown} />

<div class="manga-sequence">
  <!-- Progress bar -->
  {#if showControls}
    <div class="progress-bar">
      <div class="progress-fill" style="width: {progress}%"></div>
    </div>
  {/if}

  <!-- Panel container -->
  <div class="panel-container">
    {#if currentPanel}
      {#key currentPanel.id}
        <div class="panel-wrapper" in:fade={{ duration: 300 }}>
          <MangaPanel
            panel={currentPanel}
            active={true}
            on:click={handlePanelClick}
          />
        </div>
      {/key}
    {/if}
  </div>

  <!-- Navigation controls -->
  {#if showControls}
    <div class="controls">
      <button
        class="nav-btn prev"
        disabled={isFirst}
        on:click={previous}
        aria-label="Previous panel"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M15 18l-6-6 6-6" />
        </svg>
      </button>

      <div class="panel-indicators">
        {#each panels as panel, i}
          <button
            class="indicator"
            class:active={i === currentIndex}
            class:viewed={i < currentIndex}
            on:click={() => goTo(i)}
            aria-label="Go to panel {i + 1}"
          ></button>
        {/each}
      </div>

      <button
        class="nav-btn next"
        on:click={next}
        aria-label={isLast ? 'Complete' : 'Next panel'}
      >
        {#if isLast}
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        {:else}
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 18l6-6-6-6" />
          </svg>
        {/if}
      </button>
    </div>
  {/if}

  <!-- Tap hint -->
  <div class="tap-hint" in:fade={{ delay: 1000 }}>
    Tap to continue
  </div>

  <!-- Skip button -->
  <button class="skip-btn" on:click={() => dispatch('skip')}>
    Skip
  </button>
</div>

<style>
  .manga-sequence {
    position: relative;
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    background: #0a0a0a;
    overflow: hidden;
  }

  /* Progress bar */
  .progress-bar {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: rgba(255, 255, 255, 0.1);
    z-index: 100;
  }

  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #6366f1, #8b5cf6);
    transition: width 0.3s ease;
  }

  /* Panel container */
  .panel-container {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 16px;
    overflow: hidden;
  }

  .panel-wrapper {
    width: 100%;
    max-width: 600px;
    max-height: 100%;
  }

  /* Controls */
  .controls {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 16px;
    padding: 16px;
  }

  .nav-btn {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    border: 2px solid rgba(255, 255, 255, 0.2);
    background: rgba(255, 255, 255, 0.05);
    color: rgba(255, 255, 255, 0.8);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s ease;
  }

  .nav-btn:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.1);
    border-color: rgba(255, 255, 255, 0.4);
  }

  .nav-btn:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }

  .nav-btn svg {
    width: 20px;
    height: 20px;
  }

  /* Panel indicators */
  .panel-indicators {
    display: flex;
    gap: 6px;
  }

  .indicator {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    border: none;
    background: rgba(255, 255, 255, 0.2);
    cursor: pointer;
    transition: all 0.2s ease;
    padding: 0;
  }

  .indicator:hover {
    background: rgba(255, 255, 255, 0.4);
  }

  .indicator.active {
    background: #8b5cf6;
    transform: scale(1.2);
  }

  .indicator.viewed {
    background: rgba(139, 92, 246, 0.5);
  }

  /* Tap hint */
  .tap-hint {
    position: absolute;
    bottom: 80px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 0.85rem;
    color: rgba(255, 255, 255, 0.4);
    animation: pulse-hint 2s ease-in-out infinite;
    pointer-events: none;
  }

  @keyframes pulse-hint {
    0%, 100% { opacity: 0.4; }
    50% { opacity: 0.7; }
  }

  /* Skip button */
  .skip-btn {
    position: absolute;
    top: 16px;
    right: 16px;
    padding: 8px 16px;
    border-radius: 20px;
    border: 1px solid rgba(255, 255, 255, 0.2);
    background: rgba(0, 0, 0, 0.5);
    color: rgba(255, 255, 255, 0.6);
    font-size: 0.85rem;
    cursor: pointer;
    transition: all 0.2s ease;
    z-index: 100;
  }

  .skip-btn:hover {
    background: rgba(0, 0, 0, 0.7);
    color: rgba(255, 255, 255, 0.9);
  }

  /* Mobile adjustments */
  @media (max-width: 480px) {
    .panel-container {
      padding: 8px;
    }

    .controls {
      padding: 12px;
    }

    .nav-btn {
      width: 40px;
      height: 40px;
    }
  }
</style>
