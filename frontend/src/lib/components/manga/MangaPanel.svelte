<script>
  import { fade, fly, scale } from 'svelte/transition';
  import { createEventDispatcher } from 'svelte';

  export let panel = {
    id: '',
    type: 'full',
    scene_description: '',
    image_url: null,
    dialogue: null,
    dialogue_translation: null,
    speaker: null,
    mood: 'warm',
    effects: [],
    character_expression: null,
    duration_ms: 3000,
  };

  export let active = false;
  export let showDialogue = true;

  const dispatch = createEventDispatcher();

  // Effect classes based on panel effects
  $: effectClasses = (panel.effects || []).map(e => `effect-${e}`).join(' ');

  // Panel type determines aspect ratio and layout
  $: panelClass = `panel-${panel.type || 'full'}`;

  // Mood affects color overlay
  $: moodClass = `mood-${panel.mood || 'warm'}`;

  function handleClick() {
    dispatch('click', panel);
  }

  function handleImageLoad() {
    dispatch('loaded', panel);
  }
</script>

<div
  class="manga-panel {panelClass} {moodClass} {effectClasses}"
  class:active
  on:click={handleClick}
  on:keypress={handleClick}
  role="button"
  tabindex="0"
  transition:fade={{ duration: 300 }}
>
  <!-- Background image layer -->
  <div class="panel-image">
    {#if panel.image_url}
      <img
        src={panel.image_url}
        alt={panel.scene_description}
        on:load={handleImageLoad}
      />
    {:else}
      <div class="placeholder">
        <span class="placeholder-text">{panel.scene_description?.slice(0, 50)}...</span>
      </div>
    {/if}
  </div>

  <!-- Effect overlays -->
  {#if panel.effects?.includes('speed_lines')}
    <div class="overlay speed-lines"></div>
  {/if}

  {#if panel.effects?.includes('impact_burst')}
    <div class="overlay impact-burst"></div>
  {/if}

  {#if panel.effects?.includes('radial_zoom')}
    <div class="overlay radial-zoom"></div>
  {/if}

  {#if panel.effects?.includes('vignette')}
    <div class="overlay vignette"></div>
  {/if}

  {#if panel.effects?.includes('frozen')}
    <div class="overlay frozen"></div>
  {/if}

  {#if panel.effects?.includes('rain')}
    <div class="overlay rain"></div>
  {/if}

  {#if panel.effects?.includes('particles')}
    <div class="overlay particles">
      {#each Array(20) as _, i}
        <div
          class="particle"
          style="--delay: {i * 0.15}s; --x: {Math.random() * 100}%; --y: {Math.random() * 100}%"
        ></div>
      {/each}
    </div>
  {/if}

  <!-- Dialogue bubble -->
  {#if showDialogue && panel.dialogue}
    <div
      class="dialogue-bubble"
      class:narrator={panel.speaker === 'narrator'}
      class:bimbo={panel.speaker === 'bimbo'}
      class:npc={panel.speaker === 'npc'}
      class:player={panel.speaker === 'player'}
      in:fly={{ y: 20, duration: 300, delay: 200 }}
    >
      {#if panel.speaker && panel.speaker !== 'narrator'}
        <span class="speaker-tag">{panel.speaker}</span>
      {/if}
      <p class="dialogue-text">{panel.dialogue}</p>
      {#if panel.dialogue_translation}
        <p class="dialogue-translation">{panel.dialogue_translation}</p>
      {/if}
    </div>
  {/if}
</div>

<style>
  .manga-panel {
    position: relative;
    width: 100%;
    overflow: hidden;
    background: #0a0a0a;
    border-radius: 4px;
    cursor: pointer;
  }

  /* Panel types - aspect ratios */
  .panel-full {
    aspect-ratio: 1 / 1;
  }

  .panel-wide {
    aspect-ratio: 16 / 9;
  }

  .panel-tall {
    aspect-ratio: 9 / 16;
    max-height: 80vh;
  }

  .panel-split {
    aspect-ratio: 1 / 1;
  }

  .panel-impact {
    aspect-ratio: 1 / 1;
    max-width: 300px;
    margin: 0 auto;
  }

  .panel-transition {
    aspect-ratio: 3 / 1;
  }

  /* Image layer */
  .panel-image {
    position: absolute;
    inset: 0;
  }

  .panel-image img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .placeholder {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    padding: 20px;
  }

  .placeholder-text {
    color: rgba(255, 255, 255, 0.3);
    font-size: 0.85rem;
    text-align: center;
  }

  /* Mood color overlays */
  .mood-warm::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, rgba(255, 200, 100, 0.1) 0%, transparent 100%);
    pointer-events: none;
  }

  .mood-cold::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, rgba(100, 150, 255, 0.15) 0%, transparent 100%);
    pointer-events: none;
  }

  .mood-tense::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, rgba(200, 50, 50, 0.1) 0%, transparent 100%);
    pointer-events: none;
  }

  .mood-mysterious::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, rgba(100, 50, 150, 0.15) 0%, transparent 100%);
    pointer-events: none;
  }

  .mood-dramatic::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(to bottom, transparent 50%, rgba(0, 0, 0, 0.4) 100%);
    pointer-events: none;
  }

  .mood-hopeful::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(to top, rgba(255, 220, 150, 0.15) 0%, transparent 50%);
    pointer-events: none;
  }

  /* Effect overlays */
  .overlay {
    position: absolute;
    inset: 0;
    pointer-events: none;
  }

  .speed-lines {
    background: repeating-linear-gradient(
      90deg,
      transparent,
      transparent 10px,
      rgba(255, 255, 255, 0.03) 10px,
      rgba(255, 255, 255, 0.03) 12px
    );
    animation: speed-move 0.5s linear infinite;
  }

  @keyframes speed-move {
    from { transform: translateX(0); }
    to { transform: translateX(-24px); }
  }

  .impact-burst {
    background: radial-gradient(
      circle at center,
      rgba(255, 255, 255, 0.3) 0%,
      transparent 30%,
      transparent 100%
    );
    animation: impact-pulse 0.3s ease-out;
  }

  @keyframes impact-pulse {
    from { transform: scale(0.5); opacity: 1; }
    to { transform: scale(1.5); opacity: 0; }
  }

  .radial-zoom {
    background: radial-gradient(
      circle at center,
      transparent 30%,
      rgba(0, 0, 0, 0.1) 70%,
      rgba(0, 0, 0, 0.3) 100%
    );
  }

  .vignette {
    background: radial-gradient(
      ellipse at center,
      transparent 40%,
      rgba(0, 0, 0, 0.6) 100%
    );
  }

  .frozen {
    background: rgba(100, 100, 150, 0.1);
    filter: saturate(0.5);
  }

  .rain {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Cline x1='10' y1='0' x2='5' y2='20' stroke='rgba(200,220,255,0.3)' stroke-width='1'/%3E%3Cline x1='30' y1='10' x2='25' y2='30' stroke='rgba(200,220,255,0.2)' stroke-width='1'/%3E%3Cline x1='50' y1='5' x2='45' y2='25' stroke='rgba(200,220,255,0.25)' stroke-width='1'/%3E%3Cline x1='70' y1='15' x2='65' y2='35' stroke='rgba(200,220,255,0.2)' stroke-width='1'/%3E%3Cline x1='90' y1='0' x2='85' y2='20' stroke='rgba(200,220,255,0.3)' stroke-width='1'/%3E%3C/svg%3E");
    background-size: 50px 50px;
    animation: rain-fall 0.5s linear infinite;
  }

  @keyframes rain-fall {
    from { background-position: 0 0; }
    to { background-position: 25px 50px; }
  }

  .particles {
    overflow: hidden;
  }

  .particle {
    position: absolute;
    width: 4px;
    height: 4px;
    background: rgba(200, 180, 255, 0.6);
    border-radius: 50%;
    left: var(--x);
    top: var(--y);
    animation: float-particle 4s ease-in-out infinite;
    animation-delay: var(--delay);
  }

  @keyframes float-particle {
    0%, 100% { transform: translateY(0) scale(1); opacity: 0.3; }
    50% { transform: translateY(-20px) scale(1.2); opacity: 0.8; }
  }

  /* Dialogue bubble */
  .dialogue-bubble {
    position: absolute;
    bottom: 16px;
    left: 16px;
    right: 16px;
    background: rgba(0, 0, 0, 0.85);
    backdrop-filter: blur(8px);
    border-radius: 12px;
    padding: 12px 16px;
    border: 2px solid rgba(255, 255, 255, 0.1);
  }

  .dialogue-bubble.narrator {
    background: transparent;
    border: none;
    text-align: center;
    font-style: italic;
  }

  .dialogue-bubble.bimbo {
    background: rgba(99, 102, 241, 0.2);
    border-color: rgba(139, 92, 246, 0.4);
  }

  .dialogue-bubble.npc {
    background: rgba(0, 0, 0, 0.85);
  }

  .dialogue-bubble.player {
    background: rgba(34, 197, 94, 0.2);
    border-color: rgba(34, 197, 94, 0.4);
  }

  .speaker-tag {
    display: inline-block;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: rgba(255, 255, 255, 0.5);
    margin-bottom: 4px;
  }

  .dialogue-text {
    margin: 0;
    font-size: 1rem;
    line-height: 1.5;
    color: #ffffff;
  }

  .dialogue-translation {
    margin: 6px 0 0;
    font-size: 0.85rem;
    color: rgba(255, 255, 255, 0.6);
  }

  /* Active state */
  .manga-panel.active {
    box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.5);
  }
</style>
