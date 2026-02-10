<script>
  import { fade } from 'svelte/transition';
  import { createEventDispatcher } from 'svelte';
  import IntroDialogueBox from '../IntroDialogueBox.svelte';
  import IntroButton from '../IntroButton.svelte';
  import TapToContinue from '../TapToContinue.svelte';

  export let line = null;
  export let textComplete = false;

  const dispatch = createEventDispatcher();
</script>

<div class="scene" in:fade={{ duration: 300 }}>
  <div class="drop-flash"></div>

  {#key line}
    <IntroDialogueBox {line} variant="centered" />
  {/key}

  {#if textComplete}
    <div class="drop-transition" in:fade>
      <div class="drop-vortex"></div>
    </div>
    <IntroButton delay={500} on:click={() => dispatch('next')}>Enter</IntroButton>
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

  .drop-flash {
    position: absolute;
    inset: 0;
    background: white;
    opacity: 0;
    animation: flash 0.5s ease-out;
    pointer-events: none;
  }

  @keyframes flash {
    0% { opacity: 1; }
    100% { opacity: 0; }
  }

  .drop-transition {
    display: flex;
    justify-content: center;
    margin-bottom: 24px;
  }

  .drop-vortex {
    width: 100px;
    height: 100px;
    border: 3px solid rgba(139, 92, 246, 0.5);
    border-radius: 50%;
    animation: vortex 1s ease-in-out infinite;
  }

  @keyframes vortex {
    0% { transform: scale(0.5) rotate(0deg); opacity: 0; }
    50% { transform: scale(1) rotate(180deg); opacity: 1; }
    100% { transform: scale(0.5) rotate(360deg); opacity: 0; }
  }
</style>
