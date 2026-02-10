<script>
  import { fade } from 'svelte/transition';
  import MangaPanel from '$lib/components/manga/MangaPanel.svelte';
  import { PHASES } from './introData.js';

  export let phase = 0;
  export let activePanel = null;
  export let panelsLoaded = false;
  export let isFrozen = false;
</script>

<div class="bg-layer">
  {#if activePanel && panelsLoaded}
    <!-- Manga panel background -->
    <div class="manga-bg" class:frozen={isFrozen} transition:fade={{ duration: 600 }}>
      {#key activePanel.id}
        <MangaPanel
          panel={activePanel}
          active={true}
          showDialogue={false}
        />
      {/key}
    </div>
  {:else if phase === PHASES.FUTURE || phase === PHASES.SETUP}
    <div class="bg-future" transition:fade={{ duration: 600 }}></div>
  {:else if phase >= PHASES.DROP}
    <div class="bg-japan" class:frozen={isFrozen} transition:fade={{ duration: 600 }}></div>
  {/if}
  <div class="bg-overlay" class:frozen={isFrozen}></div>
</div>

<style>
  .bg-layer {
    position: absolute;
    inset: 0;
  }

  .bg-future {
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, #0a0a1a 0%, #1a1a2e 50%, #16213e 100%);
  }

  .bg-japan {
    position: absolute;
    inset: 0;
    background: linear-gradient(180deg, #1a1a2a 0%, #2d1f1f 50%, #1a1515 100%);
    transition: filter 0.5s ease;
  }

  .bg-japan.frozen {
    filter: saturate(0.4) brightness(0.8);
  }

  .manga-bg {
    position: absolute;
    inset: 0;
    z-index: 1;
    transition: filter 0.5s ease;
  }

  .manga-bg :global(.manga-panel) {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    border-radius: 0;
    cursor: default;
    aspect-ratio: unset;
  }

  .manga-bg :global(.manga-panel .panel-image) {
    position: absolute;
    inset: 0;
  }

  .manga-bg :global(.manga-panel .panel-image img) {
    object-fit: cover;
    width: 100%;
    height: 100%;
  }

  .manga-bg :global(.manga-panel .placeholder) {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .manga-bg.frozen {
    filter: saturate(0.4) brightness(0.8);
  }

  .manga-bg.frozen :global(.manga-panel) {
    animation: frozen-glow 3s ease-in-out infinite;
  }

  @keyframes frozen-glow {
    0%, 100% { box-shadow: inset 0 0 60px rgba(139, 92, 246, 0.2); }
    50% { box-shadow: inset 0 0 100px rgba(139, 92, 246, 0.4); }
  }

  .bg-overlay {
    position: absolute;
    inset: 0;
    background: radial-gradient(ellipse at center, transparent 30%, rgba(0,0,0,0.6) 100%);
    transition: all 0.5s ease;
    z-index: 2;
  }

  .bg-overlay.frozen {
    background: radial-gradient(ellipse at center, rgba(99, 102, 241, 0.1) 0%, rgba(30, 27, 75, 0.8) 100%);
  }
</style>
