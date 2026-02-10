<script>
  import { createEventDispatcher } from 'svelte';
  import { fly, fade } from 'svelte/transition';

  export let visible = true;
  export let message = '';
  export let isTimeStopped = true;
  export let showTools = false;
  export let requireRepeat = false;

  const dispatch = createEventDispatcher();

  let expanded = false;

  function toggleExpand() {
    expanded = !expanded;
  }

  function requestTranslate() {
    dispatch('translate');
  }

  function requestHearExample() {
    dispatch('hearExample');
  }

  function requestHint() {
    dispatch('hint');
  }

  // Thematic messages based on state (Shogun era)
  // These reinforce that struggle is meaningful, not frustrating
  const frozenMessages = [
    "Time bends to your will. This moment is yours to prepare.",
    "I could translate for you. But that's not why you're here.",
    "The struggle is the point. Take your time. Find the words.",
    "No shortcuts. No downloads. Just you and the language.",
    "In this stillness, find your voice. Earn it."
  ];

  const repeatMessages = [
    "Listen to the sounds. Let them flow through you, then speak.",
    "The tongue learns what the ear teaches. This is how it works.",
    "Close enough won't cut it. But that's what makes success real.",
    "Again. Not because I'm harsh—because you deserve to truly learn this.",
    "The hard way is the only way that matters. Try once more."
  ];

  const liveMessages = [
    "Time flows. Your words carry weight now.",
    "No more practice. This is real. This is why you came.",
    "Speak true. They're listening. You've earned this moment.",
    "The struggle was worth it. Now show them."
  ];

  function getRandomMessage(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
  }

  // Default messages based on state
  $: defaultMessage = (() => {
    if (!isTimeStopped) {
      return getRandomMessage(liveMessages);
    }
    if (requireRepeat) {
      return getRandomMessage(repeatMessages);
    }
    return getRandomMessage(frozenMessages);
  })();

  $: displayMessage = message || defaultMessage;
</script>

{#if visible}
  <div
    class="assistant-container"
    class:expanded
    transition:fly={{ y: 20, duration: 300 }}
  >
    <button class="assistant-avatar" on:click={toggleExpand} aria-label="Toggle assistant">
      <div class="avatar-glow" class:time-stopped={isTimeStopped}></div>
      <div class="avatar-face">
        <span class="avatar-emoji">🔮</span>
      </div>
      {#if !expanded}
        <div class="mini-indicator" class:live={!isTimeStopped}>
          {isTimeStopped ? '⏸' : '🔴'}
        </div>
      {/if}
    </button>

    {#if expanded}
      <div class="assistant-panel" transition:fade={{ duration: 150 }}>
        <div class="assistant-header">
          <span class="assistant-name">Bimbo</span>
          <span class="assistant-title">Time Guide</span>
        </div>

        <div class="assistant-message">
          <p>{displayMessage}</p>
        </div>

        {#if showTools && isTimeStopped}
          <div class="assistant-tools">
            <button class="tool-btn" on:click={requestHearExample}>
              <span class="tool-icon">🔊</span>
              <span class="tool-label">Hear Example</span>
            </button>
            <button class="tool-btn" on:click={requestTranslate}>
              <span class="tool-icon">🌐</span>
              <span class="tool-label">Translate</span>
            </button>
            <button class="tool-btn" on:click={requestHint}>
              <span class="tool-icon">💡</span>
              <span class="tool-label">Get Hint</span>
            </button>
          </div>
        {/if}

        <div class="time-status" class:frozen={isTimeStopped} class:live={!isTimeStopped}>
          {#if isTimeStopped}
            <span class="status-icon">⏸</span>
            <span class="status-text">Time Frozen</span>
            <span class="status-hint">Use tools freely - no consequences</span>
          {:else}
            <span class="status-icon pulse">🔴</span>
            <span class="status-text">Time Flowing</span>
            <span class="status-hint">Your words have weight</span>
          {/if}
        </div>
      </div>
    {/if}
  </div>
{/if}

<style>
  .assistant-container {
    position: fixed;
    bottom: 160px;
    left: 16px;
    z-index: 200;
    display: flex;
    align-items: flex-end;
    gap: 12px;
  }

  .assistant-avatar {
    position: relative;
    width: 56px;
    height: 56px;
    border-radius: 50%;
    border: none;
    background: transparent;
    cursor: pointer;
    padding: 0;
    transition: transform 0.2s ease;
  }

  .assistant-avatar:hover {
    transform: scale(1.1);
  }

  .avatar-glow {
    position: absolute;
    inset: -4px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(139, 92, 246, 0.4) 0%, transparent 70%);
    animation: glow-pulse 3s ease-in-out infinite;
  }

  .avatar-glow.time-stopped {
    background: radial-gradient(circle, rgba(99, 102, 241, 0.5) 0%, transparent 70%);
  }

  @keyframes glow-pulse {
    0%, 100% { opacity: 0.6; transform: scale(1); }
    50% { opacity: 1; transform: scale(1.1); }
  }

  .avatar-face {
    position: relative;
    width: 100%;
    height: 100%;
    background: linear-gradient(135deg, #1e1b4b, #312e81);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 2px solid rgba(139, 92, 246, 0.6);
    box-shadow: 0 4px 20px rgba(99, 102, 241, 0.3);
  }

  .avatar-emoji {
    font-size: 1.8rem;
    line-height: 1;
  }

  .mini-indicator {
    position: absolute;
    top: -4px;
    right: -4px;
    width: 20px;
    height: 20px;
    background: #312e81;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.7rem;
    border: 2px solid #1e1b4b;
  }

  .mini-indicator.live {
    animation: pulse-live 1s ease-in-out infinite;
  }

  @keyframes pulse-live {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.2); }
  }

  .assistant-panel {
    background: rgba(30, 27, 75, 0.95);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(139, 92, 246, 0.3);
    border-radius: 16px;
    padding: 14px;
    min-width: 240px;
    max-width: 280px;
    box-shadow: 0 8px 32px rgba(99, 102, 241, 0.2);
  }

  .assistant-header {
    display: flex;
    align-items: baseline;
    gap: 8px;
    margin-bottom: 10px;
  }

  .assistant-name {
    font-size: 1rem;
    font-weight: 700;
    color: #c4b5fd;
  }

  .assistant-title {
    font-size: 0.75rem;
    color: #8b5cf6;
    font-weight: 600;
  }

  .assistant-message {
    margin-bottom: 12px;
  }

  .assistant-message p {
    margin: 0;
    font-size: 0.9rem;
    color: #e0e7ff;
    line-height: 1.5;
  }

  .assistant-tools {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-bottom: 12px;
  }

  .tool-btn {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    padding: 10px 12px;
    background: rgba(99, 102, 241, 0.2);
    border: 1px solid rgba(99, 102, 241, 0.3);
    border-radius: 10px;
    color: #c4b5fd;
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s ease, transform 0.1s ease;
  }

  .tool-btn:hover {
    background: rgba(99, 102, 241, 0.35);
    transform: translateX(4px);
  }

  .tool-icon {
    font-size: 1rem;
  }

  .tool-label {
    flex: 1;
    text-align: left;
  }

  .time-status {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    padding: 10px 12px;
    border-radius: 10px;
    font-size: 0.85rem;
  }

  .time-status.frozen {
    background: rgba(99, 102, 241, 0.15);
    border: 1px solid rgba(99, 102, 241, 0.25);
  }

  .time-status.live {
    background: rgba(239, 68, 68, 0.15);
    border: 1px solid rgba(239, 68, 68, 0.25);
  }

  .status-icon {
    font-size: 1rem;
  }

  .status-icon.pulse {
    animation: pulse-live 1s ease-in-out infinite;
  }

  .status-text {
    font-weight: 700;
    color: #e0e7ff;
  }

  .time-status.live .status-text {
    color: #fca5a5;
  }

  .status-hint {
    width: 100%;
    font-size: 0.75rem;
    color: #a5b4fc;
    margin-top: 2px;
  }

  .time-status.live .status-hint {
    color: #fca5a5;
  }

  /* Responsive: move to bottom on smaller screens */
  @media (max-width: 480px) {
    .assistant-container {
      bottom: 200px;
      left: 12px;
    }

    .assistant-panel {
      min-width: 200px;
      max-width: 240px;
    }
  }
</style>
