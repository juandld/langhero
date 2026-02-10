<script>
  import { fly, fade } from 'svelte/transition';
  import { createEventDispatcher } from 'svelte';
  import IntroDialogueBox from '../IntroDialogueBox.svelte';
  import TapToContinue from '../TapToContinue.svelte';

  export let line = null;
  export let textComplete = false;
  export let transitioning = false;

  const dispatch = createEventDispatcher();
</script>

<div class="scene" in:fly={{ y: 20, duration: 400 }}>
  <div class="samurai-face"></div>

  {#key line}
    <IntroDialogueBox {line} />
  {/key}

  {#if textComplete}
    <!-- Time freezes automatically -->
    {#if !transitioning}
      <div class="freeze-flash" in:fade out:fade on:outroend={() => dispatch('next')}></div>
    {/if}
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

  .samurai-face {
    width: 150px;
    height: 150px;
    background: linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%);
    border-radius: 50%;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 4rem;
    border: 3px solid rgba(220, 38, 38, 0.3);
    box-shadow: 0 0 40px rgba(220, 38, 38, 0.2);
  }

  .samurai-face::after {
    content: '👺';
  }

  .freeze-flash {
    position: absolute;
    inset: 0;
    background: rgba(139, 92, 246, 0.3);
    animation: freeze-in 0.5s ease-out forwards;
    pointer-events: none;
  }

  @keyframes freeze-in {
    0% { opacity: 0; }
    50% { opacity: 1; }
    100% { opacity: 0; }
  }
</style>
