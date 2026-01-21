<script>
  import { onMount } from 'svelte';
  import { onDestroy } from 'svelte';
  import { page } from '$app/stores';
  import ScenarioDisplay from '$lib/components/ScenarioDisplay.svelte';
  import DemoModeBanner from '$lib/components/DemoModeBanner.svelte';
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

  function formatDuration(ms) {
    const n = Number(ms);
    if (!Number.isFinite(n) || n <= 0) return '0m';
    const totalSec = Math.floor(n / 1000);
    const hours = Math.floor(totalSec / 3600);
    const mins = Math.floor((totalSec % 3600) / 60);
    if (hours <= 0) return `${mins}m`;
    return `${hours}h ${mins}m`;
  }

  function copyShareLink() {
    if (!runId) return;
    const url = `${window.location.origin}/play/${encodeURIComponent(runId)}`;
    navigator.clipboard?.writeText(url).catch(() => {
      try {
        window.prompt('Copy this link:', url);
      } catch (_) {}
    });
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

<main class="play">
  <header class="top">
    <div class="run">
      <div class="title">{run?.title || 'Run'}</div>
      <div class="meta">
        <span>Time played: {formatDuration(run?.totalPlayMs || 0)}</span>
        <span>·</span>
        <button class="link" type="button" on:click={copyShareLink}>Copy share link</button>
      </div>
    </div>
  </header>
  <DemoModeBanner compact />

  {#if error === 'save_not_found'}
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
  {:else}
    <ScenarioDisplay />
  {/if}
</main>

<style>
  .play {
    font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
    max-width: 760px;
    margin: 0 auto;
    padding: 1.5rem 1.25rem 2.25rem;
  }

  .top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 14px;
  }

  .run {
    flex: 1;
    min-width: 0;
    text-align: center;
  }

  .title {
    font-weight: 950;
    letter-spacing: -0.02em;
  }

  .meta {
    margin-top: 2px;
    color: #64748b;
    font-weight: 700;
    font-size: 0.9rem;
    display: flex;
    gap: 8px;
    justify-content: center;
    align-items: center;
    flex-wrap: wrap;
  }

  .link {
    background: transparent;
    border: none;
    padding: 0;
    cursor: pointer;
    color: #111827;
    text-decoration: underline;
    font-weight: 900;
  }

  .missing {
    border: 1px solid #e2e8f0;
    background: #fff;
    border-radius: 18px;
    padding: 16px;
  }

  .missing h1 {
    margin: 0 0 6px;
    font-size: 1.1rem;
  }

  .missing p {
    margin: 0;
    color: #475569;
    font-weight: 600;
  }

  .actions {
    margin-top: 14px;
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    align-items: center;
  }

  .primary {
    background: #111827;
    color: #fff;
    text-decoration: none;
    padding: 10px 12px;
    border-radius: 12px;
    font-weight: 900;
  }

  .secondaryLink {
    color: #111827;
    font-weight: 900;
    text-decoration: underline;
  }
</style>
