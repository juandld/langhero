<script>
  import { getBackendUrl, discoverBackend } from '$lib/config';
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import { createRun } from '$lib/runStore.js';
  import DemoModeBanner from '$lib/components/DemoModeBanner.svelte';
  import { apiFetch } from '$lib/api';

  let url = '';
  let text = '';
  let setting = '';
  let targetLanguage = '';
  let maxScenes = 6;
  let attestRights = false;
  let importing = false;
  let error = '';
  let lastImportMeta = null;
  let resolvedBackend = '';

  onMount(async () => {
    resolvedBackend = getBackendUrl();
    try {
      resolvedBackend = await discoverBackend();
    } catch (_) {}
  });

  function buildRunTitle() {
    const hint = String(setting || '').trim();
    if (hint) return `Imported: ${hint}`.slice(0, 80);
    const seed = String(text || '').trim().split('\n').find(Boolean) || '';
    const clipped = seed.length > 80 ? `${seed.slice(0, 80).trim()}…` : seed;
    return clipped || 'Imported story';
  }

  function buildWebTitle(source) {
    const title = String(source?.title || '').trim();
    if (title) return `Imported: ${title}`.slice(0, 80);
    const raw = String(url || '').trim();
    if (!raw) return 'Imported web page';
    try {
      const u = new URL(raw);
      const host = u.hostname.replace(/^www\./, '');
      return `Imported: ${host}`;
    } catch (_) {
      const clipped = raw.length > 80 ? `${raw.slice(0, 80).trim()}…` : raw;
      return `Imported: ${clipped}`;
    }
  }

  function isProbablyVideoUrl(raw) {
    const u = String(raw || '').trim().toLowerCase();
    if (!u) return false;
    if (u.includes('youtube.com') || u.includes('youtu.be')) return true;
    for (const ext of ['.mp4', '.mov', '.mkv', '.webm', '.m4v', '.mp3', '.wav', '.m4a', '.ogg', '.aac', '.flac', '.m3u8']) {
      const base = u.split('?', 1)[0].split('#', 1)[0];
      if (base.endsWith(ext)) return true;
    }
    return false;
  }

  function buildAutoTitle(kind, source) {
    if (kind === 'video') {
      const raw = String(url || '').trim();
      if (!raw) return 'Imported video';
      try {
        const u = new URL(raw);
        const host = u.hostname.replace(/^www\./, '');
        const vid = u.searchParams.get('v');
        if (vid) return `Imported video: ${host} (${vid})`;
        const path = (u.pathname || '').split('/').filter(Boolean).slice(-1)[0] || '';
        if (path) return `Imported video: ${host} (${path})`;
        return `Imported video: ${host}`;
      } catch (_) {
        const clipped = raw.length > 80 ? `${raw.slice(0, 80).trim()}…` : raw;
        return `Imported video: ${clipped}`;
      }
    }
    if (kind === 'web') return buildWebTitle(source);
    return buildRunTitle();
  }

  async function importAuto() {
    error = '';
    lastImportMeta = null;
    const payload = {
      url: (url || '').trim() || null,
      text: (text || '').trim() || null,
      setting: (setting || '').trim() || null,
      target_language: (targetLanguage || '').trim() || null,
      max_scenes: Number(maxScenes) || 6,
      activate: false,
      attest_rights: Boolean(attestRights),
    };
    if (!payload.url && !payload.text) {
      error = 'Paste a URL (recommended) or some text.';
      return;
    }
    if (!payload.attest_rights) {
      error = 'Please confirm you have rights/permission to use this content.';
      return;
    }
    importing = true;
    try {
      const res = await apiFetch(`${getBackendUrl()}/api/import/auto`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = res.ok ? await res.json() : await res.json().catch(() => null);
      if (!res.ok) {
        const detail = data && (data.detail || data.error) ? String(data.detail || data.error) : `Import failed (HTTP ${res.status}).`;
        if (detail === 'demo_mode_cache_only') {
          error = 'Demo mode is cache-only for video imports. Ask an admin to pre-cache this URL, or disable DEMO_VIDEO_CACHE_ONLY.';
        } else if (detail === 'url_not_allowed') {
          error = 'That URL is not allowed (private/internal hostnames are blocked).';
        } else if (detail === 'invalid_scheme') {
          error = 'Only http/https URLs are supported.';
        } else if (detail === 'content_too_large') {
          error = 'That URL is too large to import (size cap hit).';
        } else if (detail === 'no_text_found') {
          // If we guessed wrong, hint the user to try a different URL (or use a direct media URL).
          error = isProbablyVideoUrl(payload.url)
            ? 'No readable text found; this looks like a video URL. Try again or use a direct media link.'
            : 'No readable text was found at that URL.';
        } else {
          error = detail;
        }
        return;
      }
      if (!data?.scenarios || !Array.isArray(data.scenarios) || !data.scenarios.length) {
        error = 'Import succeeded but returned no scenarios.';
        return;
      }
      lastImportMeta = {
        kind: String(data.kind || ''),
        cached: Boolean(data.cached),
        cache_saved: Boolean(data.cache_saved),
        sourceTitle: data?.source?.title || '',
        sourceFinalUrl: data?.source?.final_url || '',
      };
      const run = createRun({
        title: buildAutoTitle(String(data.kind || ''), data?.source || null),
        targetLanguage: data?.target_language || data?.targetLanguage || data?.scenarios?.[0]?.language || '',
        scenarios: data.scenarios,
        startId: data.scenarios?.[0]?.id ?? 1,
      });
      await goto(`/play/${encodeURIComponent(run.id)}`);
    } catch (_) {
      error = 'Import failed. Is the backend running?';
    } finally {
      importing = false;
    }
  }
</script>

<main class="import-page">
  <h1>Import</h1>
  <DemoModeBanner compact />
  <p class="note">
    Paste a URL (recommended) and we’ll auto-detect web vs video. Add extra text if you want to steer the import.
  </p>

  <div class="field">
    <label for="url">Source URL (recommended)</label>
    <input id="url" bind:value={url} placeholder="https://..." />
    {#if lastImportMeta?.kind === 'video'}
      <div class="hint">Detected: video · cache: {lastImportMeta.cached ? 'hit' : 'miss'}{lastImportMeta.cache_saved ? ' (saved)' : ''}</div>
    {:else if lastImportMeta?.kind === 'web'}
      <div class="hint">Detected: web page{lastImportMeta?.sourceTitle ? ` · title: ${lastImportMeta.sourceTitle}` : ''}</div>
    {/if}
  </div>

  <div class="field">
    <label for="text">Extra text (optional)</label>
    <textarea id="text" bind:value={text} rows="6" placeholder="Optional: transcript, summary, or constraints..." />
  </div>

  <div class="grid">
    <div class="field">
      <label for="setting">Setting hint (optional)</label>
      <input id="setting" bind:value={setting} placeholder="e.g., Feudal Japan, Madrid, NYC..." />
      <div class="hint">Used for language inference; you can override below.</div>
    </div>
    <div class="field">
      <label for="language">Target language (optional override)</label>
      <select id="language" bind:value={targetLanguage}>
        <option value="">Auto</option>
        <option value="English">English</option>
        <option value="Spanish">Spanish</option>
        <option value="Japanese">Japanese</option>
      </select>
      <div class="hint">Auto chooses based on setting/page/text heuristics.</div>
    </div>
    <div class="field">
      <label for="scenes">Max scenes</label>
      <input id="scenes" type="number" min="1" max="12" step="1" bind:value={maxScenes} />
      <div class="hint">Small numbers keep the first MVP fast.</div>
    </div>
  </div>

  <div class="field checkbox">
    <label>
      <input type="checkbox" bind:checked={attestRights} />
      I have the rights/permission to use this content.
    </label>
  </div>

  {#if error}
    <div class="error" role="alert">{error}</div>
  {/if}

  <div class="actions">
    <button type="button" disabled={importing} on:click={importAuto}>
      {importing ? 'Importing…' : 'Import'}
    </button>
    <a class="link" href="/">Menu</a>
    <a class="link" href="/demo">Demo</a>
    {#if resolvedBackend}
      <span class="backend">Backend: <code>{resolvedBackend}</code></span>
    {/if}
  </div>
</main>

<style>
  .import-page {
    font-family: sans-serif;
    max-width: 860px;
    margin: 0 auto;
    padding: 2rem 1.25rem;
  }

  h1 {
    margin: 0 0 0.5rem;
    text-align: center;
  }

  .note {
    margin: 0 0 1.25rem;
    text-align: center;
    color: #6b7280;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-bottom: 12px;
  }

  label {
    font-weight: 700;
    color: #111827;
  }

  textarea,
  input,
  select {
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    padding: 10px 12px;
    font-size: 0.95rem;
  }

  textarea {
    resize: vertical;
    min-height: 180px;
  }

  .hint {
    font-size: 0.85rem;
    color: #6b7280;
  }

  .grid {
    display: grid;
    grid-template-columns: 1.2fr 1fr 0.6fr;
    gap: 12px;
  }

  @media (max-width: 860px) {
    .grid {
      grid-template-columns: 1fr;
    }
  }

  .checkbox {
    margin-top: 6px;
  }

  .checkbox label {
    font-weight: 600;
    color: #374151;
    display: flex;
    gap: 10px;
    align-items: center;
  }

  .error {
    background: #fee2e2;
    color: #b91c1c;
    padding: 10px 12px;
    border-radius: 12px;
    margin: 10px 0 12px;
    font-weight: 600;
  }

  .actions {
    display: flex;
    gap: 12px;
    align-items: center;
    flex-wrap: wrap;
    justify-content: center;
    margin-top: 10px;
  }

  button {
    background: #111827;
    color: white;
    border: none;
    padding: 10px 14px;
    border-radius: 10px;
    cursor: pointer;
    font-weight: 700;
  }

  button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .link {
    color: #111827;
    text-decoration: underline;
    font-weight: 700;
  }

  .backend {
    font-size: 0.85rem;
    color: #6b7280;
  }

  code {
    background: #f3f4f6;
    padding: 2px 6px;
    border-radius: 6px;
  }
</style>
