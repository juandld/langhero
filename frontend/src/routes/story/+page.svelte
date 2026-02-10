<script>
  /**
   * Story Mode Entry Point
   *
   * This route provides the full narrative experience:
   *   intro → tutorial → transition → story_intro → drop → playing
   *
   * Default story is Shogun (Japanese).
   */
  import { StoryOrchestrator } from '$lib/components/story';

  // Default to Shogun story for now
  // Later can be configured via query params or user selection
  const storyId = 'shogun';
  const language = 'Japanese';
</script>

<StoryOrchestrator {storyId} {language} />

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    overflow: hidden;
    background: #0f172a;
  }
</style>
