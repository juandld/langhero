<script>
  import { fly, fade } from 'svelte/transition';
  import { createEventDispatcher } from 'svelte';
  import IntroDialogueBox from '../IntroDialogueBox.svelte';
  import IntroButton from '../IntroButton.svelte';
  import TapToContinue from '../TapToContinue.svelte';

  export let line = null;
  export let textComplete = false;

  const dispatch = createEventDispatcher();
</script>

<div class="scene" in:fly={{ y: 20, duration: 400 }}>
  <div class="hologram-display">
    <div class="holo-image"></div>
    <div class="holo-scanline"></div>
  </div>

  {#key line}
    <IntroDialogueBox {line} />
  {/key}

  {#if textComplete}
    <div class="choice-buttons" in:fade={{ delay: 200 }}>
      <IntroButton variant="continue" on:click={() => dispatch('next')}>
        Let's do it
      </IntroButton>
    </div>
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
  }

  .hologram-display {
    width: 100%;
    height: 180px;
    background: rgba(99, 102, 241, 0.1);
    border: 1px solid rgba(99, 102, 241, 0.3);
    border-radius: 12px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
  }

  .holo-image {
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, rgba(139, 92, 246, 0.2) 0%, rgba(99, 102, 241, 0.1) 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 4rem;
    opacity: 0.5;
  }

  .holo-image::after {
    content: '⛩️';
  }

  .holo-scanline {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, rgba(139, 92, 246, 0.8), transparent);
    animation: scan 2s linear infinite;
  }

  @keyframes scan {
    0% { top: 0; }
    100% { top: 100%; }
  }

  .choice-buttons {
    display: flex;
    gap: 12px;
  }
</style>
