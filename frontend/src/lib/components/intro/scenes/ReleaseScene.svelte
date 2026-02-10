<script>
  import { fly, fade } from 'svelte/transition';
  import { createEventDispatcher } from 'svelte';
  import IntroDialogueBox from '../IntroDialogueBox.svelte';
  import IntroButton from '../IntroButton.svelte';

  export let line = null;
  export let showReleaseButton = false;

  const dispatch = createEventDispatcher();
</script>

<div class="scene" in:fly={{ y: 20, duration: 400 }}>
  {#key line}
    <IntroDialogueBox {line} variant="bimbo" />
  {/key}

  {#if showReleaseButton}
    <IntroButton variant="release" delay={300} on:click={() => dispatch('release')}>
      RELEASE TIME & SPEAK
    </IntroButton>
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
