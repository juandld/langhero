<script>
  /**
   * Story Mode with explicit storyId.
   *
   * Shogun test uses story-panels for visuals while preserving the
   * existing story/game flow to avoid breaking the default route.
   */
  import { page } from '$app/stores';
  import { StoryOrchestrator } from '$lib/components/story';

  const language = 'Japanese';

  $: routeStoryId = $page.params.storyId;
  $: isShogunTest = routeStoryId === 'shogun_test';
  $: storyId = isShogunTest ? 'shogun' : routeStoryId;
  $: panelStoryId = isShogunTest ? 'shogun_test' : null;
  $: panelSource = isShogunTest ? 'story-panels' : 'legacy';
</script>

<StoryOrchestrator {storyId} {language} {panelStoryId} {panelSource} />

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    overflow: hidden;
    background: #0f172a;
  }
</style>
