<script>
  import GameView from '$lib/components/game/GameView.svelte';
  import { storyStore } from '$lib/storyStore.js';
  import { getStreamMode } from '$lib/config';
  import { onMount } from 'svelte';

  let streamMode = 'real';
  let devPanelVisible = true;

  onMount(() => {
    streamMode = getStreamMode();
    storyStore.useBuiltInScenarios();
  });

  const jumpTo = (id) => storyStore.goToScenario(id);
  const reset = () => storyStore.useBuiltInScenarios();
  const toggleDevPanel = () => { devPanelVisible = !devPanelVisible; };
</script>

<div class="demo-container">
  <GameView />

  {#if devPanelVisible}
    <div class="dev-overlay">
      <div class="dev-panel">
        <button class="close-btn" on:click={toggleDevPanel} aria-label="Close dev panel">×</button>
        <h2>Demo Controls</h2>
        <p class="hint">Jump between beginner and advanced scenarios</p>
        <div class="controls">
          <button type="button" on:click={() => jumpTo(1)}>Beginner (1)</button>
          <button type="button" on:click={() => jumpTo(4)}>Advanced (4)</button>
          <button type="button" class="secondary" on:click={reset}>Reset</button>
        </div>
        <div class="stream-info">
          Stream: <code>{streamMode}</code>
        </div>
      </div>
    </div>
  {:else}
    <button class="show-dev-btn" on:click={toggleDevPanel} aria-label="Show dev panel">
      DEV
    </button>
  {/if}
</div>

<style>
  .demo-container {
    position: relative;
    width: 100%;
    height: 100vh;
  }

  .dev-overlay {
    position: fixed;
    top: 60px;
    right: 16px;
    z-index: 500;
  }

  .dev-panel {
    background: rgba(15, 23, 42, 0.95);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    padding: 16px;
    min-width: 220px;
    color: #e2e8f0;
    font-family: system-ui, -apple-system, sans-serif;
  }

  .dev-panel h2 {
    margin: 0 0 8px;
    font-size: 1rem;
    font-weight: 700;
    color: #f8fafc;
  }

  .hint {
    margin: 0 0 12px;
    font-size: 0.8rem;
    color: #94a3b8;
  }

  .controls {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  button {
    background: #6366f1;
    color: white;
    border: none;
    padding: 10px 14px;
    border-radius: 10px;
    cursor: pointer;
    font-size: 0.9rem;
    font-weight: 600;
    transition: background 0.15s ease;
  }

  button:hover {
    background: #4f46e5;
  }

  button.secondary {
    background: #475569;
  }

  button.secondary:hover {
    background: #64748b;
  }

  .close-btn {
    position: absolute;
    top: 8px;
    right: 8px;
    background: transparent;
    border: none;
    color: #94a3b8;
    font-size: 1.5rem;
    padding: 4px 8px;
    cursor: pointer;
    line-height: 1;
  }

  .close-btn:hover {
    color: #e2e8f0;
    background: transparent;
  }

  .stream-info {
    margin-top: 12px;
    font-size: 0.8rem;
    color: #94a3b8;
    text-align: center;
  }

  code {
    background: rgba(255, 255, 255, 0.1);
    padding: 2px 6px;
    border-radius: 4px;
    color: #a5b4fc;
  }

  .show-dev-btn {
    position: fixed;
    top: 60px;
    right: 16px;
    z-index: 500;
    background: rgba(99, 102, 241, 0.8);
    color: white;
    border: none;
    padding: 8px 12px;
    border-radius: 8px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    cursor: pointer;
  }

  .show-dev-btn:hover {
    background: #6366f1;
  }
</style>
