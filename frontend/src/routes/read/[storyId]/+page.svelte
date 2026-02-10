<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { fade, fly } from 'svelte/transition';

  const API_BASE = 'http://localhost:8000';

  let story = null;
  let currentChapterIndex = 0;
  let currentPanelIndex = 0;
  let loading = true;
  let error = null;
  let showVocab = false;

  $: storyId = $page.params.storyId;
  $: currentChapter = story?.chapters?.[currentChapterIndex];
  $: currentPanel = currentChapter?.panels?.[currentPanelIndex];
  $: totalPanels = story?.chapters?.reduce((sum, ch) => sum + ch.panels.length, 0) || 0;

  // Calculate current panel number (must reference reactive vars directly)
  $: currentPanelNumber = (() => {
    if (!story) return 0;
    let count = 0;
    for (let i = 0; i < currentChapterIndex; i++) {
      count += story.chapters[i].panels.length;
    }
    return count + currentPanelIndex + 1;
  })();

  $: progress = totalPanels > 0 ? (currentPanelNumber / totalPanels) * 100 : 0;

  onMount(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/story-panels/stories/${storyId}`);
      if (!res.ok) throw new Error('Story not found');
      story = await res.json();
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  function nextPanel() {
    showVocab = false;
    if (currentPanelIndex < currentChapter.panels.length - 1) {
      currentPanelIndex++;
    } else if (currentChapterIndex < story.chapters.length - 1) {
      currentChapterIndex++;
      currentPanelIndex = 0;
    }
  }

  function prevPanel() {
    showVocab = false;
    if (currentPanelIndex > 0) {
      currentPanelIndex--;
    } else if (currentChapterIndex > 0) {
      currentChapterIndex--;
      currentPanelIndex = story.chapters[currentChapterIndex].panels.length - 1;
    }
  }

  function handleKeydown(e) {
    if (e.key === 'ArrowRight' || e.key === ' ') {
      e.preventDefault();
      nextPanel();
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      prevPanel();
    }
  }

  function handleClick(e) {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    if (x > rect.width / 2) {
      nextPanel();
    } else {
      prevPanel();
    }
  }

  function getSpeakerName(speaker) {
    const names = {
      bimbo: 'Bimbo',
      hana: 'Hana',
      kenji: 'Kenji',
      player: 'You',
    };
    return names[speaker] || speaker;
  }

  function getSpeakerColor(speaker) {
    const colors = {
      bimbo: '#a855f7',
      hana: '#78716c',
      kenji: '#1e40af',
      player: '#10b981',
    };
    return colors[speaker] || '#fff';
  }
</script>

<svelte:window on:keydown={handleKeydown} />

<div class="reader">
  {#if loading}
    <div class="loading">Loading story...</div>
  {:else if error}
    <div class="error">{error}</div>
  {:else if story}
    <!-- Progress bar -->
    <div class="progress-bar">
      <div class="progress-fill" style="width: {progress}%"></div>
    </div>

    <!-- Chapter title -->
    {#key currentChapter?.id}
      <div class="chapter-title" in:fade={{ duration: 300 }}>
        {currentChapter?.title}
      </div>
    {/key}

    <!-- Panel display -->
    <div class="panel-container" on:click={handleClick}>
      {#key currentPanel?.id}
        <div
          class="panel panel--{currentPanel?.aspect || 'square'}"
          class:panel--time-freeze={currentPanel?.effect === 'time_freeze'}
          class:panel--time-resume={currentPanel?.effect === 'time_resume'}
          in:fade={{ duration: 400 }}
        >
          <img
            src="{API_BASE}{currentPanel?.image}"
            alt={currentPanel?.id}
            class="panel-image"
          />

          <!-- Time freeze/resume overlay -->
          {#if currentPanel?.effect === 'time_freeze'}
            <div class="effect-overlay freeze">
              <span>TIME FREEZE</span>
            </div>
          {/if}
          {#if currentPanel?.effect === 'time_resume'}
            <div class="effect-overlay resume">
              <span>TIME RESUMES</span>
            </div>
          {/if}
        </div>
      {/key}
    </div>

    <!-- Text box -->
    <div class="text-box">
      {#key currentPanel?.id}
        <div class="text-content" in:fly={{ y: 20, duration: 300 }}>
          {#if currentPanel?.narration}
            <p class="narration">{currentPanel.narration}</p>
          {/if}
          {#if currentPanel?.dialogue}
            <p class="dialogue">
              {#if currentPanel?.speaker}
                <span class="speaker" style="color: {getSpeakerColor(currentPanel.speaker)}">
                  {getSpeakerName(currentPanel.speaker)}:
                </span>
              {/if}
              "{currentPanel.dialogue}"
            </p>
          {/if}

          <!-- Vocab card -->
          {#if currentPanel?.vocab}
            <button class="vocab-toggle" on:click|stopPropagation={() => showVocab = !showVocab}>
              {showVocab ? 'Hide' : 'Show'} Vocabulary
            </button>
            {#if showVocab}
              <div class="vocab-card" transition:fly={{ y: 10, duration: 200 }}>
                <div class="vocab-word">{currentPanel.vocab.word}</div>
                <div class="vocab-reading">{currentPanel.vocab.reading}</div>
                <div class="vocab-meaning">{currentPanel.vocab.meaning}</div>
                {#if currentPanel.vocab.note}
                  <div class="vocab-note">{currentPanel.vocab.note}</div>
                {/if}
              </div>
            {/if}
          {/if}
        </div>
      {/key}
    </div>

    <!-- Navigation hint -->
    <div class="nav-hint">
      <span>← Previous</span>
      <span class="panel-number">Panel {currentPanelNumber} of {totalPanels}</span>
      <span>Next →</span>
    </div>
  {/if}
</div>

<style>
  .reader {
    min-height: 100vh;
    background: #0a0a0a;
    color: #fff;
    display: flex;
    flex-direction: column;
    font-family: 'Segoe UI', system-ui, sans-serif;
  }

  .loading, .error {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100vh;
    font-size: 1.2rem;
  }

  .error {
    color: #ef4444;
  }

  .progress-bar {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: #1f1f1f;
    z-index: 100;
  }

  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #a855f7, #06b6d4);
    transition: width 0.3s ease;
  }

  .chapter-title {
    position: fixed;
    top: 12px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 0.875rem;
    color: #a1a1aa;
    z-index: 50;
    text-align: center;
  }

  .panel-container {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 3rem 1rem 1rem;
    cursor: pointer;
    min-height: 50vh;
  }

  .panel {
    position: relative;
    max-width: 100%;
    max-height: 60vh;
    border-radius: 4px;
    overflow: hidden;
    box-shadow: 0 10px 40px rgba(0,0,0,0.5);
  }

  .panel--wide {
    max-width: min(900px, 95vw);
  }

  .panel--square {
    max-width: min(500px, 90vw);
  }

  .panel--tall {
    max-width: min(400px, 80vw);
    max-height: 70vh;
  }

  .panel--time-freeze {
    animation: freeze-pulse 2s ease-in-out infinite;
  }

  .panel--time-resume {
    animation: resume-flash 0.5s ease-out;
  }

  @keyframes freeze-pulse {
    0%, 100% { box-shadow: 0 0 20px rgba(6, 182, 212, 0.3); }
    50% { box-shadow: 0 0 40px rgba(6, 182, 212, 0.6); }
  }

  @keyframes resume-flash {
    0% { filter: brightness(2); }
    100% { filter: brightness(1); }
  }

  .panel-image {
    display: block;
    width: 100%;
    height: auto;
  }

  .effect-overlay {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-size: 1.5rem;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 0.2em;
    padding: 0.5rem 1.5rem;
    border-radius: 4px;
    animation: effect-appear 0.5s ease-out;
  }

  .effect-overlay.freeze {
    background: rgba(6, 182, 212, 0.8);
    color: #fff;
    text-shadow: 0 0 10px rgba(6, 182, 212, 1);
  }

  .effect-overlay.resume {
    background: rgba(239, 68, 68, 0.8);
    color: #fff;
  }

  @keyframes effect-appear {
    0% { opacity: 0; transform: translate(-50%, -50%) scale(0.8); }
    100% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
  }

  .text-box {
    background: linear-gradient(to top, rgba(0,0,0,0.95), rgba(0,0,0,0.8));
    padding: 1.5rem;
    min-height: 150px;
  }

  .text-content {
    max-width: 700px;
    margin: 0 auto;
  }

  .narration {
    font-size: 1rem;
    line-height: 1.7;
    color: #d4d4d8;
    margin: 0 0 0.75rem 0;
    font-style: italic;
  }

  .dialogue {
    font-size: 1.1rem;
    line-height: 1.6;
    color: #fff;
    margin: 0;
  }

  .speaker {
    font-weight: 600;
    margin-right: 0.5rem;
  }

  .vocab-toggle {
    margin-top: 1rem;
    padding: 0.5rem 1rem;
    background: #27272a;
    border: 1px solid #3f3f46;
    border-radius: 4px;
    color: #a1a1aa;
    cursor: pointer;
    font-size: 0.875rem;
    transition: all 0.2s;
  }

  .vocab-toggle:hover {
    background: #3f3f46;
    color: #fff;
  }

  .vocab-card {
    margin-top: 1rem;
    padding: 1rem;
    background: linear-gradient(135deg, #1e1b4b, #0f172a);
    border: 1px solid #4c1d95;
    border-radius: 8px;
  }

  .vocab-word {
    font-size: 2rem;
    font-weight: bold;
    color: #c4b5fd;
  }

  .vocab-reading {
    font-size: 1.1rem;
    color: #a78bfa;
    margin-top: 0.25rem;
  }

  .vocab-meaning {
    font-size: 1rem;
    color: #e2e8f0;
    margin-top: 0.5rem;
  }

  .vocab-note {
    font-size: 0.875rem;
    color: #94a3b8;
    margin-top: 0.5rem;
    font-style: italic;
  }

  .nav-hint {
    display: flex;
    justify-content: space-between;
    padding: 0.75rem 1.5rem;
    font-size: 0.75rem;
    color: #52525b;
    background: #0a0a0a;
  }

  .panel-number {
    color: #a1a1aa;
    font-weight: 600;
    background: #1f1f1f;
    padding: 0.25rem 0.75rem;
    border-radius: 4px;
  }

  /* Mobile adjustments */
  @media (max-width: 640px) {
    .panel-container {
      padding: 2.5rem 0.5rem 0.5rem;
    }

    .panel {
      max-height: 50vh;
    }

    .text-box {
      padding: 1rem;
      min-height: 120px;
    }

    .narration {
      font-size: 0.9rem;
    }

    .dialogue {
      font-size: 1rem;
    }
  }
</style>
