<script>
  import ScenarioDisplay from '$lib/components/ScenarioDisplay.svelte';
  import { storyStore } from '$lib/storyStore.js';
  import { getStreamMode } from '$lib/config';
  import { onMount } from 'svelte';
  import DemoModeBanner from '$lib/components/DemoModeBanner.svelte';

  let streamMode = 'real';

  onMount(() => {
    streamMode = getStreamMode();
    storyStore.useBuiltInScenarios();
  });

  const jumpTo = (id) => storyStore.goToScenario(id);
  const reset = () => storyStore.useBuiltInScenarios();
</script>

<main class="demo">
  <h1>Scenario Mode Demo</h1>
  <DemoModeBanner compact />
  <p class="note">
    Jump between a beginner (time-stop) and advanced (streaming) scenario to sanity-check the HUD + controls.
  </p>

  <div class="controls">
    <button type="button" on:click={() => jumpTo(1)}>Beginner (Scenario 1)</button>
    <button type="button" on:click={() => jumpTo(4)}>Advanced (Scenario 4)</button>
    <button type="button" class="secondary" on:click={reset}>Reset</button>
  </div>

  <div class="hint">
    Stream mode: <code>{streamMode}</code> (set via <code>?stream=real|mock|off</code>) · Dev back button via
    <code>?dev=1</code>
  </div>

  <ScenarioDisplay />
</main>

<style>
  .demo {
    font-family: sans-serif;
    max-width: 760px;
    margin: 0 auto;
    padding: 2rem 1.25rem;
  }

  h1 {
    margin: 0 0 0.5rem;
    text-align: center;
  }

  .note {
    margin: 0 0 1rem;
    text-align: center;
    color: #6b7280;
  }

  .controls {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    justify-content: center;
    margin-bottom: 0.75rem;
  }

  button {
    background: #111827;
    color: white;
    border: none;
    padding: 10px 14px;
    border-radius: 10px;
    cursor: pointer;
  }

  button.secondary {
    background: #374151;
  }

  .hint {
    margin: 0 auto 1.25rem;
    max-width: 620px;
    font-size: 0.9rem;
    color: #374151;
    text-align: center;
  }

  code {
    background: #f3f4f6;
    padding: 2px 6px;
    border-radius: 6px;
  }
</style>
