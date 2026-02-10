<script>
  import { fly } from 'svelte/transition';
  import { createEventDispatcher } from 'svelte';
  import IntroDialogueBox from '../IntroDialogueBox.svelte';
  import IntroButton from '../IntroButton.svelte';
  import TapToContinue from '../TapToContinue.svelte';

  export let line = null;
  export let textComplete = false;

  const dispatch = createEventDispatcher();

  // Generate random particle positions once
  const particles = Array.from({ length: 12 }, (_, i) => ({
    delay: i * 0.2,
    x: Math.random() * 100,
    y: Math.random() * 100
  }));
</script>

<div class="scene" in:fly={{ y: 20, duration: 400 }}>
  <div class="frozen-particles">
    {#each particles as p}
      <div class="particle" style="--delay: {p.delay}s; --x: {p.x}%; --y: {p.y}%"></div>
    {/each}
  </div>

  {#key line}
    <IntroDialogueBox {line} variant="bimbo" />
  {/key}

  {#if textComplete}
    <IntroButton variant="frozen" on:click={() => dispatch('next')}>Show me</IntroButton>
  {:else}
    <TapToContinue on:tap={() => dispatch('advance')} />
  {/if}
</div>

<style>
  .scene {
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 100%;
    position: relative;
  }

  .frozen-particles {
    position: absolute;
    inset: 0;
    pointer-events: none;
  }

  .particle {
    position: absolute;
    width: 4px;
    height: 4px;
    background: rgba(199, 210, 254, 0.6);
    border-radius: 50%;
    left: var(--x);
    top: var(--y);
    animation: float-particle 4s ease-in-out infinite;
    animation-delay: var(--delay);
  }

  @keyframes float-particle {
    0%, 100% { transform: translateY(0); opacity: 0.3; }
    50% { transform: translateY(-15px); opacity: 0.8; }
  }
</style>
