<script>
  import { fly } from 'svelte/transition';
  import { createEventDispatcher } from 'svelte';
  import IntroDialogueBox from '../IntroDialogueBox.svelte';
  import IntroButton from '../IntroButton.svelte';
  import TapToContinue from '../TapToContinue.svelte';

  export let line = null;
  export let textComplete = false;

  const dispatch = createEventDispatcher();
</script>

<div class="scene" in:fly={{ y: 20, duration: 400 }}>
  <div class="future-viewport">
    <div class="stars"></div>
  </div>

  {#key line}
    <IntroDialogueBox {line} />
  {/key}

  {#if textComplete}
    <IntroButton on:click={() => dispatch('next')}>Continue</IntroButton>
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

  .future-viewport {
    width: 100%;
    height: 150px;
    background: linear-gradient(180deg, #000 0%, #0a0a1a 100%);
    border-radius: 12px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
  }

  .stars {
    position: absolute;
    inset: 0;
    background-image:
      radial-gradient(1px 1px at 20% 30%, white, transparent),
      radial-gradient(1px 1px at 40% 70%, white, transparent),
      radial-gradient(1px 1px at 50% 20%, white, transparent),
      radial-gradient(1.5px 1.5px at 70% 60%, white, transparent),
      radial-gradient(1px 1px at 80% 40%, white, transparent),
      radial-gradient(1.5px 1.5px at 90% 80%, white, transparent);
    animation: twinkle 4s ease-in-out infinite;
  }

  @keyframes twinkle {
    0%, 100% { opacity: 0.7; }
    50% { opacity: 1; }
  }
</style>
