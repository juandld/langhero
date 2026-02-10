<script>
  import { onMount } from 'svelte';
  import { onDestroy } from 'svelte';
  import { page } from '$app/stores';
  import GameView from '$lib/components/game/GameView.svelte';
  import { addPlayTime, getRun, runsStore, setActiveRun, syncFromStorage, updateRun } from '$lib/runStore.js';
  import { storyStore } from '$lib/storyStore.js';

  let run = null;
  let error = '';
  let mounted = false;
  let lastLoadedId = null;

  let lastScenarioId = null;
  let tickStartedAt = 0;
  let timer = null;
  let unsubStory = null;

  function loadRun(id) {
    error = '';
    syncFromStorage();
    setActiveRun(id);
    run = getRun(id);
    if (!run) {
      error = 'save_not_found';
      return;
    }
    storyStore.loadScenarios(run.scenarios, { startId: run.currentScenarioId });
    updateRun(id, { title: run.title });
  }

  $: runId = $page?.params?.id || null;
  $: if (runId && $runsStore?.length) {
    const fromStore = $runsStore.find((r) => r && r.id === runId) || null;
    if (fromStore) run = fromStore;
  }
  $: if (mounted && runId && runId !== lastLoadedId) {
    lastLoadedId = runId;
    loadRun(runId);
  }

  function startTracking() {
    tickStartedAt = Date.now();
    timer = setInterval(() => {
      if (!runId) return;
      const now = Date.now();
      addPlayTime(runId, now - tickStartedAt);
      tickStartedAt = now;
    }, 15000);

    unsubStory = storyStore.subscribe((s) => {
      if (!runId) return;
      const sid = typeof s?.id === 'number' ? s.id : null;
      if (!sid || sid === lastScenarioId) return;
      lastScenarioId = sid;
      updateRun(runId, { currentScenarioId: sid, targetLanguage: s?.language || undefined });
    });
  }

  onDestroy(() => {
    mounted = false;
    try {
      if (timer) clearInterval(timer);
      timer = null;
    } catch (_) {}
    try {
      if (unsubStory) unsubStory();
      unsubStory = null;
    } catch (_) {}
    if (runId && tickStartedAt) {
      const now = Date.now();
      addPlayTime(runId, now - tickStartedAt);
      tickStartedAt = now;
    }
  });

  onMount(() => {
    mounted = true;
    if (runId && runId !== lastLoadedId) {
      lastLoadedId = runId;
      loadRun(runId);
    }
    startTracking();
  });
</script>

{#if error === 'save_not_found'}
  <main class="play error-page">
    <section class="missing">
      <h1>Save not found on this device</h1>
      <p>
        This link is shareable, but saves currently live in local browser storage. Once login is wired up, these links
        will resolve anywhere.
      </p>
      <div class="actions">
        <a class="primary" href="/">Go to menu</a>
        <a class="secondaryLink" href="/import">Import a story</a>
        <a class="secondaryLink" href="/demo">Try demo</a>
      </div>
    </section>
  </main>
{:else}
  <GameView />
{/if}

<style>
  .play.error-page {
    font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
    max-width: 760px;
    margin: 0 auto;
    padding: 1.5rem 1.25rem 2.25rem;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .missing {
    border: 1px solid #e2e8f0;
    background: #fff;
    border-radius: 18px;
    padding: 24px;
    text-align: center;
    max-width: 400px;
  }

  .missing h1 {
    margin: 0 0 12px;
    font-size: 1.2rem;
    color: #0f172a;
  }

  .missing p {
    margin: 0;
    color: #475569;
    font-weight: 500;
    line-height: 1.5;
  }

  .actions {
    margin-top: 20px;
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    align-items: center;
    justify-content: center;
  }

  .primary {
    background: #111827;
    color: #fff;
    text-decoration: none;
    padding: 12px 20px;
    border-radius: 12px;
    font-weight: 700;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
  }

  .primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  }

  .secondaryLink {
    color: #111827;
    font-weight: 700;
    text-decoration: underline;
  }
</style>
