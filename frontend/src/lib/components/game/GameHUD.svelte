<script>
  import { createEventDispatcher } from 'svelte';

  export let lives = 3;
  export let livesTotal = 3;
  export let score = 0;

  const dispatch = createEventDispatcher();

  function openMenu() {
    dispatch('openMenu');
  }

  $: heartsArray = Array(livesTotal).fill(0).map((_, i) => i < lives ? 'full' : 'empty');
</script>

<div class="game-hud">
  <button class="menu-btn" on:click={openMenu} aria-label="Open game menu" title="Menu (ESC)">
    <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
      <path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/>
    </svg>
  </button>

  <div class="right-hud">
    <div class="score">
      <span class="score-value">{score}</span>
    </div>
    <div class="hearts" aria-label="{lives} of {livesTotal} lives remaining">
      {#each heartsArray as heart}
        <span class="heart" class:empty={heart === 'empty'}>
          {heart === 'full' ? '❤️' : '🖤'}
        </span>
      {/each}
    </div>
  </div>
</div>

<style>
  .game-hud {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding: 12px 16px;
    z-index: 100;
    pointer-events: none;
  }

  .menu-btn {
    pointer-events: auto;
    background: rgba(0, 0, 0, 0.5);
    border: none;
    border-radius: 10px;
    padding: 10px;
    color: white;
    cursor: pointer;
    backdrop-filter: blur(8px);
    transition: transform 0.15s ease, background 0.15s ease;
  }

  .menu-btn:hover {
    background: rgba(0, 0, 0, 0.7);
    transform: scale(1.05);
  }

  .menu-btn svg {
    display: block;
  }

  .right-hud {
    pointer-events: auto;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 6px;
  }

  .score {
    background: rgba(0, 0, 0, 0.5);
    backdrop-filter: blur(8px);
    padding: 6px 12px;
    border-radius: 20px;
    color: #fbbf24;
    font-weight: 700;
    font-size: 0.95rem;
    letter-spacing: 0.02em;
  }

  .hearts {
    display: flex;
    gap: 4px;
    background: rgba(0, 0, 0, 0.4);
    backdrop-filter: blur(8px);
    padding: 6px 10px;
    border-radius: 20px;
  }

  .heart {
    font-size: 1.1rem;
    line-height: 1;
    transition: transform 0.2s ease, opacity 0.2s ease;
  }

  .heart.empty {
    opacity: 0.5;
    filter: grayscale(1);
  }
</style>
