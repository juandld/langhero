<script>
  /**
   * Saved Runs Management
   *
   * View, continue, publish, and manage saved game runs.
   */
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import scenarios from '$lib/test/scenarios.json';
  import { getBackendUrl, discoverBackend } from '$lib/config';
  import { apiFetch } from '$lib/api';
  import { activeRunId, createRun, deleteRun, runsStore, setActiveRun, syncFromStorage, updateRun } from '$lib/runStore.js';
  import { clamp01 } from '$lib/utils';

  let confirmingDelete = null;
  let publishingRunId = null;
  let publishError = '';
  let resolvedBackend = '';
  let shareModalRunId = null;

  onMount(() => {
    syncFromStorage();
    resolvedBackend = getBackendUrl();
    discoverBackend().then((u) => { resolvedBackend = u; }).catch(() => {});
  });

  function formatWhen(ts) {
    const n = Number(ts);
    if (!Number.isFinite(n) || n <= 0) return '—';
    try {
      return new Date(n).toLocaleString();
    } catch (_) {
      return '—';
    }
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

  function summary(run) {
    const list = Array.isArray(run?.scenarios) ? run.scenarios : [];
    const currentId = Number(run?.currentScenarioId);
    const idx = list.findIndex((s) => s && typeof s === 'object' && s.id === currentId);
    const current = (idx >= 0 ? list[idx] : list[0]) || {};
    const dialogue = String(
      current.character_dialogue_en ||
        current.character_dialogue_jp ||
        current.description ||
        '',
    ).trim();
    const short = dialogue.length > 88 ? `${dialogue.slice(0, 88).trim()}…` : dialogue;
    return {
      total: list.length || 0,
      index: idx >= 0 ? idx + 1 : 1,
      situation: short || '—',
    };
  }

  function startDemoRun() {
    const run = createRun({
      title: 'Demo: Built-in scenarios',
      targetLanguage: 'Japanese',
      scenarios,
      startId: 1,
    });
    goto(`/play/${encodeURIComponent(run.id)}`);
  }

  async function continueRun(id) {
    setActiveRun(id);
    await goto(`/play/${encodeURIComponent(id)}`);
  }

  function requestDelete(id) {
    confirmingDelete = id;
  }

  function cancelDelete() {
    confirmingDelete = null;
  }

  function confirmDelete(id) {
    deleteRun(id);
    confirmingDelete = null;
  }

  async function copyPrivateLink(id) {
    const path = `/play/${encodeURIComponent(id)}`;
    const url = typeof window !== 'undefined' ? `${window.location.origin}${path}` : path;
    try {
      await navigator.clipboard.writeText(url);
    } catch (_) {
      try {
        window.prompt('Copy this link:', url);
      } catch (_) {}
    }
  }

  async function copyShareLink(publicId) {
    const path = `/share/${encodeURIComponent(publicId)}`;
    const url = typeof window !== 'undefined' ? `${window.location.origin}${path}` : path;
    try {
      await navigator.clipboard.writeText(url);
    } catch (_) {
      try {
        window.prompt('Copy this link:', url);
      } catch (_) {}
    }
  }

  async function publishRun(run) {
    publishError = '';
    const id = run?.id;
    if (!id) return;
    if (publishingRunId) return;

    const ok = window.confirm(
      'Publish this run to create a public share link?\n\n' +
        '- This makes the compiled scenario chain publicly retrievable.\n' +
        '- Only publish if you have rights/permission to share it.\n\n' +
        'Continue?',
    );
    if (!ok) return;
    const ok2 = window.confirm('Final check: you confirm you have rights/permission to publish this content?');
    if (!ok2) return;

    publishingRunId = id;
    try {
      const res = await apiFetch(`${getBackendUrl()}/api/published_runs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: run.title || 'Published run',
          target_language: run.targetLanguage || '',
          scenarios: run.scenarios || [],
          attest_rights: true,
          confirm_publish: true,
        }),
      });
      const data = res.ok ? await res.json() : await res.json().catch(() => null);
      if (!res.ok) {
        publishError = (data && (data.detail || data.error)) ? String(data.detail || data.error) : `Publish failed (HTTP ${res.status})`;
        return;
      }
      const publicId = data?.public_id || data?.publicId || '';
      const deleteKey = data?.delete_key || data?.deleteKey || '';
      if (!publicId) {
        publishError = 'Publish succeeded but returned no public id.';
        return;
      }
      updateRun(id, {
        publishedPublicId: String(publicId),
        publishedDeleteKey: String(deleteKey || ''),
        publishedAt: Date.now(),
      });
      shareModalRunId = id;
      await copyShareLink(publicId);
    } catch (_) {
      publishError = 'Publish failed. Is the backend running?';
    } finally {
      publishingRunId = null;
    }
  }

  async function unpublishRun(run) {
    publishError = '';
    const id = run?.id;
    const publicId = String(run?.publishedPublicId || '').trim();
    const deleteKey = String(run?.publishedDeleteKey || '').trim();
    if (!id || !publicId || !deleteKey) {
      publishError = 'Missing publish delete key for this run.';
      return;
    }
    const ok = window.confirm('Unpublish this share link? It will stop working for anyone who has it.');
    if (!ok) return;
    try {
      const res = await apiFetch(`${getBackendUrl()}/api/published_runs/${encodeURIComponent(publicId)}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ delete_key: deleteKey }),
      });
      const data = res.ok ? await res.json() : await res.json().catch(() => null);
      if (!res.ok) {
        publishError = (data && (data.detail || data.error)) ? String(data.detail || data.error) : `Unpublish failed (HTTP ${res.status})`;
        return;
      }
      updateRun(id, { publishedPublicId: '', publishedDeleteKey: '', publishedAt: 0 });
      if (shareModalRunId === id) shareModalRunId = null;
    } catch (_) {
      publishError = 'Unpublish failed. Is the backend running?';
    }
  }

  function openShareModal(id) {
    shareModalRunId = id;
  }

  function closeShareModal() {
    shareModalRunId = null;
  }

  $: shareModalRun =
    shareModalRunId && Array.isArray($runsStore)
      ? ($runsStore.find((r) => r && r.id === shareModalRunId) || null)
      : null;
</script>

<main class="saves-page">
  <header class="header">
    <a href="/" class="back-link">
      <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
        <path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/>
      </svg>
      Back
    </a>
    <h1 class="title">Saved Runs</h1>
  </header>

  <section class="panel">
    <div class="panel-head">
      <h2>Your Adventures</h2>
      <div style="display: flex; gap: 0.5rem;">
        <a href="/read/shogun_test" class="secondary" style="text-decoration: none;">Read Visual Novel</a>
        <button class="secondary" type="button" on:click={startDemoRun}>New demo run</button>
      </div>
    </div>

    {#if publishError}
      <div class="panel-error" role="alert">
        {publishError}
        {#if resolvedBackend}
          <span class="panel-error-meta">Backend: <code>{resolvedBackend}</code></span>
        {/if}
      </div>
    {/if}

    {#if !$runsStore.length}
      <div class="empty">
        <div class="empty-title">No saves yet.</div>
        <div class="empty-body">
          Start your journey from the main menu to create your first save.
        </div>
        <div class="empty-actions">
          <a class="primary" href="/">Go to Main Menu</a>
          <a class="secondary-link" href="/import">Import story</a>
        </div>
      </div>
    {:else}
      <div class="grid">
        {#each $runsStore as run (run.id)}
          {@const meta = summary(run)}
          {@const focus = clamp01(run.judgeFocus)}
          {@const progressPct = meta.total > 0 ? Math.round((meta.index / meta.total) * 100) : 0}
          <article class={`card ${$activeRunId === run.id ? 'active' : ''}`}>
            <div class="card-head">
              <div class="name">{run.title}</div>
              {#if $activeRunId === run.id}
                <div class="badge">Active</div>
              {/if}
            </div>

            <div class="meta">
              <div><span class="k">Language</span> <span class="v">{run.targetLanguage || '—'}</span></div>
              <div><span class="k">Last played</span> <span class="v">{formatWhen(run.updatedAt)}</span></div>
              <div><span class="k">Time played</span> <span class="v">{formatDuration(run.totalPlayMs)}</span></div>
              <div><span class="k">Progress</span> <span class="v">{meta.index}/{meta.total} ({progressPct}%)</span></div>
            </div>

            <div class="situation">
              <div class="k">Current situation</div>
              <div class="v">{meta.situation}</div>
            </div>

            <div class="focus">
              <div class="focus-head">
                <div class="k">Learning / Story</div>
                <div class="v">{Math.round(focus * 100)}%</div>
              </div>
              <div class="focus-bar" aria-label="Learning vs story focus">
                <div class="focus-fill" style={`width:${Math.round(focus * 100)}%`} />
                <div class="focus-dot" style={`left:${Math.round(focus * 100)}%`} />
              </div>
              <div class="focus-labels">
                <span>Learning</span>
                <span>Story</span>
              </div>
            </div>

            <div class="actions">
              <button type="button" class="primary" on:click={() => continueRun(run.id)}>Play</button>
              <button type="button" class="secondary" on:click={() => copyPrivateLink(run.id)}>Copy link</button>
              {#if run.publishedPublicId}
                <button type="button" class="secondary" on:click={() => copyShareLink(run.publishedPublicId)}>Share link</button>
                <button type="button" class="secondary" on:click={() => openShareModal(run.id)}>Details</button>
              {:else}
                <button type="button" class="secondary" disabled={publishingRunId === run.id} on:click={() => publishRun(run)}>
                  {publishingRunId === run.id ? 'Publishing…' : 'Publish'}
                </button>
              {/if}
              {#if confirmingDelete === run.id}
                <button type="button" class="danger" on:click={() => confirmDelete(run.id)}>Confirm</button>
                <button type="button" class="secondary" on:click={cancelDelete}>Cancel</button>
              {:else}
                <button type="button" class="secondary danger-text" on:click={() => requestDelete(run.id)}>Delete</button>
              {/if}
            </div>
          </article>
        {/each}
      </div>
    {/if}
  </section>

  {#if shareModalRun?.publishedPublicId}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div class="modalBackdrop" on:click={closeShareModal}>
      <div class="modal" role="dialog" aria-modal="true" aria-label="Share details" on:click|stopPropagation>
        <div class="modalHead">
          <div class="modalTitle">Share details</div>
          <button class="modalClose" type="button" on:click={closeShareModal} aria-label="Close">×</button>
        </div>
        <div class="modalBody">
          <div class="modalRow">
            <div class="k">Run</div>
            <div class="v">{shareModalRun.title}</div>
          </div>
          <div class="modalRow">
            <div class="k">Public link</div>
            <div class="v">
              <code>/share/{shareModalRun.publishedPublicId}</code>
              <button class="mini" type="button" on:click={() => copyShareLink(shareModalRun.publishedPublicId)}>Copy</button>
            </div>
          </div>
          {#if shareModalRun.publishedDeleteKey}
            <div class="modalRow">
              <div class="k">Delete key</div>
              <div class="v">
                <code>{String(shareModalRun.publishedDeleteKey).slice(0, 10)}…</code>
                <button class="mini" type="button" on:click={() => navigator.clipboard?.writeText(shareModalRun.publishedDeleteKey).catch(() => {})}>
                  Copy
                </button>
              </div>
            </div>
          {/if}
          <div class="modalNote">
            Publishing makes this run publicly retrievable. Keep the delete key private.
          </div>
          <div class="modalActions">
            <button class="danger" type="button" on:click={() => unpublishRun(shareModalRun)}>Unpublish</button>
            <button class="secondary" type="button" on:click={closeShareModal}>Close</button>
          </div>
        </div>
      </div>
    </div>
  {/if}
</main>

<style>
  .saves-page {
    font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
    max-width: 980px;
    margin: 0 auto;
    padding: 1.5rem 1.25rem 3rem;
    min-height: 100vh;
    background: #0a0a1a;
    color: #e2e8f0;
  }

  .header {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 24px;
  }

  .back-link {
    display: flex;
    align-items: center;
    gap: 6px;
    color: #94a3b8;
    text-decoration: none;
    font-weight: 600;
    padding: 8px 12px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 10px;
    transition: all 0.15s ease;
  }

  .back-link:hover {
    background: rgba(255, 255, 255, 0.1);
    color: #e2e8f0;
  }

  .title {
    font-size: 1.5rem;
    font-weight: 800;
    margin: 0;
    color: #f8fafc;
  }

  .panel {
    background: #0f172a;
    border-radius: 20px;
    padding: 20px;
    border: 1px solid rgba(148, 163, 184, 0.15);
  }

  .panel-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 16px;
  }

  .panel-head h2 {
    margin: 0;
    font-size: 1rem;
    font-weight: 700;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  .panel-error {
    margin: 0 0 16px;
    background: rgba(239, 68, 68, 0.12);
    border: 1px solid rgba(248, 113, 113, 0.4);
    border-radius: 12px;
    padding: 12px;
    color: #fca5a5;
    font-weight: 600;
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    align-items: center;
  }

  .panel-error-meta {
    color: #e2e8f0;
    font-weight: 600;
    font-size: 0.85rem;
  }

  .empty {
    background: rgba(255, 255, 255, 0.03);
    border: 1px dashed rgba(255, 255, 255, 0.15);
    border-radius: 16px;
    padding: 24px;
    text-align: center;
  }

  .empty-title {
    font-size: 1.1rem;
    font-weight: 700;
    margin-bottom: 8px;
    color: #f8fafc;
  }

  .empty-body {
    color: #94a3b8;
    font-weight: 500;
    margin-bottom: 16px;
  }

  .empty-actions {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    justify-content: center;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 16px;
  }

  .card {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(148, 163, 184, 0.15);
    border-radius: 16px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .card.active {
    border-color: rgba(99, 102, 241, 0.5);
    box-shadow: 0 0 20px rgba(99, 102, 241, 0.15);
  }

  .card-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }

  .name {
    font-weight: 700;
    font-size: 1.05rem;
    color: #f8fafc;
  }

  .badge {
    font-size: 0.7rem;
    font-weight: 700;
    padding: 4px 8px;
    border-radius: 20px;
    background: rgba(99, 102, 241, 0.2);
    border: 1px solid rgba(99, 102, 241, 0.4);
    color: #a5b4fc;
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  .meta {
    display: grid;
    gap: 4px;
    font-size: 0.9rem;
  }

  .k {
    color: #64748b;
    font-weight: 600;
    margin-right: 6px;
  }

  .v {
    color: #e2e8f0;
    font-weight: 500;
  }

  .situation {
    padding: 10px;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 10px;
  }

  .situation .k {
    display: block;
    margin-bottom: 4px;
    font-size: 0.8rem;
  }

  .situation .v {
    color: #cbd5e1;
    font-size: 0.9rem;
    line-height: 1.4;
  }

  .focus-head {
    display: flex;
    justify-content: space-between;
    font-size: 0.85rem;
    margin-bottom: 6px;
  }

  .focus-bar {
    position: relative;
    height: 8px;
    border-radius: 4px;
    background: rgba(255, 255, 255, 0.1);
    overflow: visible;
  }

  .focus-fill {
    height: 100%;
    border-radius: 4px;
    background: linear-gradient(90deg, #22c55e, #6366f1);
  }

  .focus-dot {
    position: absolute;
    top: 50%;
    transform: translate(-50%, -50%);
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: #0f172a;
    border: 2px solid #e2e8f0;
  }

  .focus-labels {
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
    color: #64748b;
    font-weight: 600;
    margin-top: 4px;
  }

  .actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-top: 4px;
  }

  button, a.primary, a.secondary-link {
    border: none;
    border-radius: 10px;
    padding: 10px 14px;
    cursor: pointer;
    font-weight: 700;
    font-size: 0.9rem;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s ease;
  }

  .primary {
    background: #f8fafc;
    color: #0f172a;
  }

  .primary:hover {
    background: #e2e8f0;
  }

  .secondary {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.15);
    color: #e2e8f0;
  }

  .secondary:hover {
    background: rgba(255, 255, 255, 0.1);
  }

  .secondary-link {
    background: transparent;
    color: #a5b4fc;
    text-decoration: underline;
  }

  .danger {
    background: rgba(239, 68, 68, 0.15);
    border: 1px solid rgba(248, 113, 113, 0.4);
    color: #fca5a5;
  }

  .danger:hover {
    background: rgba(239, 68, 68, 0.25);
  }

  .danger-text {
    color: #f87171;
  }

  .mini {
    padding: 6px 10px;
    border-radius: 8px;
    font-size: 0.8rem;
  }

  .modalBackdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.7);
    backdrop-filter: blur(4px);
    display: grid;
    place-items: center;
    padding: 20px;
    z-index: 1000;
  }

  .modal {
    width: min(500px, calc(100vw - 40px));
    border-radius: 16px;
    background: #0f172a;
    border: 1px solid rgba(148, 163, 184, 0.2);
    overflow: hidden;
  }

  .modalHead {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px;
    border-bottom: 1px solid rgba(148, 163, 184, 0.15);
  }

  .modalTitle {
    font-weight: 700;
    font-size: 1.05rem;
  }

  .modalClose {
    background: rgba(255, 255, 255, 0.08);
    border: none;
    color: #94a3b8;
    border-radius: 8px;
    padding: 6px 10px;
    cursor: pointer;
    font-size: 1.2rem;
  }

  .modalBody {
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .modalRow {
    display: grid;
    grid-template-columns: 100px 1fr;
    gap: 12px;
    align-items: center;
  }

  .modalRow .v {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
  }

  .modalNote {
    color: #94a3b8;
    font-size: 0.85rem;
    font-weight: 500;
    padding: 10px;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 8px;
  }

  .modalActions {
    display: flex;
    gap: 10px;
    justify-content: flex-end;
    margin-top: 8px;
  }

  code {
    background: rgba(255, 255, 255, 0.08);
    padding: 4px 8px;
    border-radius: 6px;
    font-size: 0.85rem;
  }
</style>
