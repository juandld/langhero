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

<div class="scene" in:fly={{ y: 20, duration: 400, delay: 300 }}>
  {#key line}
    <IntroDialogueBox {line} />
  {/key}

  {#if textComplete}
    <IntroButton variant="start" delay={300} on:click={() => dispatch('complete')}>
      Begin your journey
    </IntroButton>
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
</style>
