<script>
  import { fly, fade } from 'svelte/transition';
  import { createEventDispatcher } from 'svelte';
  import IntroDialogueBox from '../IntroDialogueBox.svelte';
  import IntroButton from '../IntroButton.svelte';
  import PhraseCard from '../PhraseCard.svelte';

  export let line = null;
  export let textComplete = false;
  export let hasListened = false;
  export let hasPracticed = false;
  export let isRecording = false;

  const dispatch = createEventDispatcher();
</script>

<div class="scene" in:fly={{ y: 20, duration: 400 }}>
  {#key line}
    <IntroDialogueBox {line} variant="bimbo" />
  {/key}

  <PhraseCard
    {hasListened}
    {hasPracticed}
    {isRecording}
    on:listen={() => dispatch('listen')}
    on:practice={() => dispatch('practice')}
  />

  {#if hasPracticed && textComplete}
    <IntroButton variant="frozen" delay={300} on:click={() => dispatch('next')}>
      I'm ready
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
