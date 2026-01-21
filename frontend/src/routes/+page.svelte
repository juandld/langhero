<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import scenarios from '$lib/test/scenarios.json';
  import { getBackendUrl, discoverBackend } from '$lib/config';
  import DemoModeBanner from '$lib/components/DemoModeBanner.svelte';
  import { activeRunId, createRun, deleteRun, runsStore, setActiveRun, syncFromStorage, updateRun } from '$lib/runStore.js';

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

  function clamp01(v) {
    const n = Number(v);
    if (!Number.isFinite(n)) return 0;
    return Math.max(0, Math.min(1, n));
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
      // best-effort fallback
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

    // Explicit publish confirmation: public retrievable artifact.
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
      const res = await fetch(`${getBackendUrl()}/api/published_runs`, {
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
      const res = await fetch(`${getBackendUrl()}/api/published_runs/${encodeURIComponent(publicId)}`, {
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

<main class="menu">
  <header class="hero">
    <div class="title">Main Menu</div>
    <div class="subtitle">Choose a run, resume, or import a new story.</div>
  </header>

  <section class="panel">
    <DemoModeBanner compact />
    <div class="panel-head">
      <h2>Saved runs</h2>
      <button class="secondary" type="button" on:click={startDemoRun}>Start demo run</button>
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
          Import a story to create your first run, or start the demo run to explore the UI.
        </div>
        <div class="empty-actions">
          <a class="primary" href="/import">Import story</a>
          <button type="button" class="secondary" on:click={startDemoRun}>Start demo run</button>
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
                <div class="k">Learning ↔ Story</div>
                <div class="v">{Math.round(focus * 100)}%</div>
              </div>
              <div class="focus-bar" aria-label="Learning vs story focus">
                <div class="focus-fill" style={`width:${Math.round(focus * 100)}%`} />
                <div class="focus-dot" style={`left:${Math.round(focus * 100)}%`} />
              </div>
              <div class="focus-labels">
                <span>Learning-first</span>
                <span>Story-first</span>
              </div>
            </div>

            <div class="actions">
              <button type="button" class="primary" on:click={() => continueRun(run.id)}>Play</button>
              <button type="button" class="secondary" on:click={() => copyPrivateLink(run.id)}>Copy private link</button>
              {#if run.publishedPublicId}
                <button type="button" class="secondary" on:click={() => copyShareLink(run.publishedPublicId)}>Copy share link</button>
                <button type="button" class="secondary" on:click={() => openShareModal(run.id)}>Share details</button>
              {:else}
                <button type="button" class="secondary" disabled={publishingRunId === run.id} on:click={() => publishRun(run)}>
                  {publishingRunId === run.id ? 'Publishing…' : 'Publish'}
                </button>
              {/if}
              {#if confirmingDelete === run.id}
                <button type="button" class="danger" on:click={() => confirmDelete(run.id)}>Confirm delete</button>
                <button type="button" class="secondary" on:click={cancelDelete}>Cancel</button>
              {:else}
                <button type="button" class="secondary" on:click={() => requestDelete(run.id)}>Delete</button>
              {/if}
            </div>
          </article>
        {/each}
      </div>
    {/if}
  </section>

  {#if shareModalRun?.publishedPublicId}
    <div class="modalBackdrop" role="presentation" on:click={closeShareModal}>
      <div class="modal" role="dialog" aria-modal="true" aria-label="Share details" on:click|stopPropagation>
        <div class="modalHead">
          <div class="modalTitle">Share details</div>
          <button class="modalClose" type="button" on:click={closeShareModal} aria-label="Close">✕</button>
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
            <button class="danger" type="button" on:click={() => unpublishRun(shareModalRun)}>Unpublish link</button>
            <button class="secondary" type="button" on:click={closeShareModal}>Close</button>
          </div>
        </div>
      </div>
    </div>
  {/if}
</main>

<style>
  .menu {
    font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, 'Apple Color Emoji', 'Segoe UI Emoji';
    max-width: 980px;
    margin: 0 auto;
    padding: 2.25rem 1.25rem 3rem;
    color: #0f172a;
  }

  .hero {
    margin-bottom: 1.25rem;
  }

  .title {
    font-size: 1.75rem;
    font-weight: 900;
    letter-spacing: -0.02em;
  }

  .subtitle {
    margin-top: 4px;
    color: #64748b;
    font-weight: 600;
  }

  .panel {
    background: #0b1220;
    border-radius: 22px;
    padding: 18px;
    border: 1px solid rgba(148, 163, 184, 0.2);
    box-shadow: 0 18px 40px rgba(15, 23, 42, 0.28);
  }

  .panel-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 14px;
    color: #e2e8f0;
  }

  .panel-error {
    margin: 0 0 12px;
    background: rgba(239, 68, 68, 0.12);
    border: 1px solid rgba(248, 113, 113, 0.45);
    border-radius: 14px;
    padding: 10px 12px;
    color: #fecaca;
    font-weight: 800;
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    align-items: center;
  }

  .panel-error-meta {
    color: #e2e8f0;
    font-weight: 700;
    font-size: 0.85rem;
  }

  h2 {
    margin: 0;
    font-size: 1.05rem;
    letter-spacing: 0.02em;
    text-transform: uppercase;
  }

  .empty {
    background: #111827;
    border: 1px dashed rgba(226, 232, 240, 0.35);
    border-radius: 18px;
    padding: 18px;
    color: #e2e8f0;
  }

  .empty-title {
    font-size: 1.1rem;
    font-weight: 900;
    margin-bottom: 6px;
  }

  .empty-body {
    color: #cbd5e1;
    font-weight: 600;
  }

  .empty-actions {
    margin-top: 14px;
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 14px;
  }

  @media (max-width: 980px) {
    .grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 720px) {
    .top {
      flex-direction: column;
      align-items: flex-start;
    }
    .grid {
      grid-template-columns: 1fr;
    }
  }

  .card {
    background: #111827;
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 18px;
    padding: 14px 14px 12px;
    color: #e2e8f0;
    backdrop-filter: blur(8px);
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .card.active {
    border-color: rgba(96, 165, 250, 0.9);
    box-shadow: 0 10px 24px rgba(59, 130, 246, 0.25);
  }

  .card-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }

  .name {
    font-weight: 900;
    font-size: 1.05rem;
    line-height: 1.1;
  }

  .badge {
    font-size: 0.75rem;
    font-weight: 900;
    padding: 6px 9px;
    border-radius: 999px;
    background: rgba(59, 130, 246, 0.15);
    border: 1px solid rgba(96, 165, 250, 0.7);
    color: #bfdbfe;
    white-space: nowrap;
  }

  .meta {
    display: grid;
    grid-template-columns: 1fr;
    gap: 6px;
    font-size: 0.92rem;
  }

  .k {
    color: #cbd5e1;
    font-weight: 800;
    margin-right: 6px;
  }

  .v {
    color: #f8fafc;
    font-weight: 650;
  }

  .situation .v {
    color: #e5e7eb;
  }

  .focus-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
  }

  .focus-bar {
    position: relative;
    height: 10px;
    border-radius: 999px;
    background: rgba(148, 163, 184, 0.25);
    overflow: hidden;
    margin-top: 8px;
  }

  .focus-fill {
    height: 100%;
    background: linear-gradient(90deg, rgba(34, 197, 94, 0.85), rgba(59, 130, 246, 0.9));
  }

  .focus-dot {
    position: absolute;
    top: 50%;
    transform: translate(-50%, -50%);
    width: 14px;
    height: 14px;
    border-radius: 999px;
    background: #0b1220;
    border: 2px solid rgba(226, 232, 240, 0.9);
    box-shadow: 0 6px 14px rgba(15, 23, 42, 0.35);
  }

  .focus-labels {
    display: flex;
    justify-content: space-between;
    color: #94a3b8;
    font-weight: 800;
    font-size: 0.8rem;
    margin-top: 6px;
  }

  .actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-top: 2px;
  }

  button,
  a.primary {
    border: none;
    border-radius: 12px;
    padding: 10px 12px;
    cursor: pointer;
    font-weight: 900;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }

  .primary {
    background: #f8fafc;
    color: #0b1220;
  }

  .primary:hover {
    background: #e2e8f0;
  }

  .secondary {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(226, 232, 240, 0.25);
    color: #e2e8f0;
  }

  .secondary:hover {
    background: rgba(255, 255, 255, 0.1);
  }

  .danger {
    background: rgba(239, 68, 68, 0.15);
    border: 1px solid rgba(248, 113, 113, 0.6);
    color: #fecaca;
  }

  .danger:hover {
    background: rgba(239, 68, 68, 0.22);
  }

  .mini {
    padding: 6px 10px;
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(226, 232, 240, 0.25);
    color: #e2e8f0;
    font-weight: 900;
  }

  .modalBackdrop {
    position: fixed;
    inset: 0;
    background: rgba(2, 6, 23, 0.66);
    display: grid;
    place-items: center;
    padding: 18px;
    z-index: 10000;
  }

  .modal {
    width: min(680px, calc(100vw - 36px));
    border-radius: 18px;
    background: #0b1220;
    border: 1px solid rgba(148, 163, 184, 0.22);
    box-shadow: 0 22px 70px rgba(15, 23, 42, 0.62);
    color: #e2e8f0;
    overflow: hidden;
  }

  .modalHead {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 14px;
    border-bottom: 1px solid rgba(148, 163, 184, 0.18);
  }

  .modalTitle {
    font-weight: 950;
    letter-spacing: -0.02em;
  }

  .modalClose {
    background: rgba(255, 255, 255, 0.08);
    color: #e2e8f0;
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 12px;
    padding: 8px 10px;
    cursor: pointer;
    font-weight: 950;
  }

  .modalBody {
    padding: 14px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .modalRow {
    display: grid;
    grid-template-columns: 110px 1fr;
    gap: 10px;
    align-items: center;
  }

  .modalRow .v {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
  }

  .modalNote {
    color: #cbd5e1;
    font-weight: 700;
    font-size: 0.9rem;
    margin-top: 2px;
  }

  .modalActions {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    justify-content: flex-end;
    margin-top: 8px;
  }
</style>
