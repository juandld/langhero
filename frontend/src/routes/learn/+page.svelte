<script>
  import GameView from '$lib/components/game/GameView.svelte';
  import { storyStore } from '$lib/storyStore.js';
  import { onMount } from 'svelte';

  onMount(() => {
    storyStore.useBuiltInScenarios();
  });
</script>

<svelte:head>
  <title>Learn - LangHero</title>
</svelte:head>

<GameView />
