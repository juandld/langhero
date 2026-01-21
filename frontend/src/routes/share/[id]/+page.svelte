<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { getBackendUrl, discoverBackend } from '$lib/config';
  import { createRun } from '$lib/runStore.js';

  let loading = true;
  let error = '';
  let published = null;
  let resolvedBackend = '';

  $: publicId = $page?.params?.id || '';

  onMount(async () => {
    resolvedBackend = getBackendUrl();
    try {
      resolvedBackend = await discoverBackend();
    } catch (_) {}
    await fetchPublished();
  });

  async function fetchPublished() {
    loading = true;
    error = '';
    published = null;
    try {
      const res = await fetch(`${getBackendUrl()}/api/published_runs/${encodeURIComponent(publicId)}`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });
      const data = res.ok ? await res.json() : await res.json().catch(() => null);
      if (!res.ok) {
        error = (data && (data.detail || data.error)) ? String(data.detail || data.error) : `Not found (HTTP ${res.status})`;
        return;
      }
      published = data;
    } catch (_) {
      error = 'Failed to load share link. Is the backend running?';
    } finally {
      loading = false;
    }
  }

  function summarizeScene(scene) {
    const s = scene || {};
    const raw = String(s.character_dialogue_en || s.character_dialogue_jp || s.description || '').trim();
    if (!raw) return '—';
    return raw.length > 110 ? `${raw.slice(0, 110).trim()}…` : raw;
  }

  async function saveToMyRuns() {
    if (!published?.scenarios?.length) return;
    const run = createRun({
      title: String(published.title || 'Shared run'),
      targetLanguage: String(published.target_language || published.targetLanguage || published?.scenarios?.[0]?.language || ''),
      scenarios: published.scenarios,
      startId: published.scenarios?.[0]?.id ?? 1,
    });
    await goto(`/play/${encodeURIComponent(run.id)}`);
  }
</script>

<main class="share">
  <section class="panel">
    <div class="title">Shared story</div>
    {#if loading}
      <div class="state">Loading…</div>
    {:else if error}
      <div class="state error" role="alert">
        <div class="h">Link not available</div>
        <div class="p">{error}</div>
        {#if resolvedBackend}
          <div class="p">Backend: <code>{resolvedBackend}</code></div>
        {/if}
      </div>
    {:else}
      <div class="hero">
        <div class="name">{published?.title || 'Shared run'}</div>
        <div class="meta">
          <span>Target language: <strong>{published?.target_language || '—'}</strong></span>
          <span>·</span>
          <span>Scenes: <strong>{published?.scenarios?.length || 0}</strong></span>
        </div>
        <div class="notice">
          This link contains a compiled scenario chain. If you didn’t create it, only use it if you trust the source.
        </div>
        <div class="actions">
          <button class="primary" type="button" on:click={saveToMyRuns}>Save to my runs &amp; play</button>
          <button class="secondary" type="button" on:click={fetchPublished}>Reload</button>
        </div>
      </div>

      <div class="preview">
        <h2>Preview</h2>
        <ol>
          {#each (published?.scenarios || []).slice(0, 4) as scene (scene.id)}
            <li>
              <div class="sceneHead">
                <span class="sceneId">#{scene.id}</span>
                <span class={`mode ${String(scene.mode || 'beginner')}`}>{String(scene.mode || 'beginner')}</span>
              </div>
              <div class="sceneBody">{summarizeScene(scene)}</div>
            </li>
          {/each}
        </ol>
      </div>
    {/if}
  </section>
</main>

<style>
  .share {
    font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
    max-width: 860px;
    margin: 0 auto;
    padding: 1.75rem 1.25rem 2.5rem;
    color: #0f172a;
  }

  .title {
    font-weight: 950;
    letter-spacing: -0.02em;
    text-align: center;
    margin: 0 0 12px;
  }

  .panel {
    border: 1px solid #e2e8f0;
    border-radius: 20px;
    background: #fff;
    padding: 16px;
  }

  .state {
    color: #475569;
    font-weight: 700;
  }

  .state.error {
    background: #fff1f2;
    border: 1px solid #fecdd3;
    padding: 12px;
    border-radius: 14px;
  }

  .state .h {
    font-weight: 900;
    margin-bottom: 4px;
    color: #9f1239;
  }

  .state .p {
    color: #475569;
    font-weight: 650;
  }

  code {
    background: #f1f5f9;
    padding: 2px 6px;
    border-radius: 8px;
  }

  .hero .name {
    font-size: 1.25rem;
    font-weight: 950;
    letter-spacing: -0.02em;
  }

  .meta {
    margin-top: 4px;
    color: #64748b;
    font-weight: 700;
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    align-items: center;
  }

  .notice {
    margin-top: 12px;
    color: #475569;
    font-weight: 650;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    padding: 10px 12px;
    border-radius: 14px;
  }

  .actions {
    margin-top: 12px;
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
  }

  button {
    border: none;
    border-radius: 12px;
    padding: 10px 12px;
    cursor: pointer;
    font-weight: 900;
  }

  .primary {
    background: #111827;
    color: #fff;
  }

  .secondary {
    background: #e2e8f0;
    color: #0f172a;
  }

  .preview {
    margin-top: 14px;
  }

  h2 {
    margin: 0 0 8px;
    font-size: 0.95rem;
    text-transform: uppercase;
    letter-spacing: 0.02em;
    color: #475569;
  }

  ol {
    margin: 0;
    padding-left: 18px;
    display: grid;
    gap: 10px;
  }

  li {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 10px 12px;
  }

  .sceneHead {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;
    color: #475569;
    font-weight: 800;
  }

  .sceneId {
    font-variant-numeric: tabular-nums;
  }

  .mode {
    text-transform: uppercase;
    font-size: 0.75rem;
    letter-spacing: 0.02em;
    padding: 4px 8px;
    border-radius: 999px;
    border: 1px solid #cbd5e1;
    background: #fff;
  }

  .mode.advanced {
    border-color: #c7d2fe;
    background: #eef2ff;
    color: #3730a3;
  }

  .sceneBody {
    color: #0f172a;
    font-weight: 650;
  }
</style>
