<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { getRun, syncFromStorage } from '$lib/runStore.js';

  function clipId(id) {
    const s = String(id || '').trim();
    if (!s) return '';
    if (s.length <= 10) return s;
    return `${s.slice(0, 6)}…${s.slice(-2)}`;
  }

  function titleForPlayId(id) {
    try {
      const run = getRun(String(id || ''));
      return run?.title ? String(run.title) : '';
    } catch (_) {
      return '';
    }
  }

  onMount(() => {
    syncFromStorage();
  });

  $: path = $page?.url?.pathname || '/';
  $: parts = path.split('/').filter(Boolean);
  $: kind = parts[0] || '';
  $: id = parts[1] || '';

  $: crumbs = (() => {
    /** @type {{ label: string, href: string | null }[]} */
    const out = [{ label: 'Menu', href: '/' }];
    if (!kind) return out;

    if (kind === 'play' && id) {
      out.push({ label: 'Play', href: null });
      const title = titleForPlayId(id);
      out.push({ label: title || clipId(id) || 'Run', href: null });
      return out;
    }

    if (kind === 'share' && id) {
      out.push({ label: 'Share', href: null });
      out.push({ label: clipId(id) || 'Link', href: null });
      return out;
    }

    const labelMap = {
      import: 'Import',
      demo: 'Demo',
      login: 'Login',
      learn: 'Learn',
      menu: 'Menu',
    };
    out.push({ label: labelMap[kind] || kind, href: null });
    return out;
  })();
</script>

<div class="crumbs" aria-label="Breadcrumbs">
  {#each crumbs as c, idx (idx)}
    {#if idx !== 0}
      <span class="sep">/</span>
    {/if}
    {#if c.href}
      <a class="crumb" href={c.href}>{c.label}</a>
    {:else}
      <span class="crumb current">{c.label}</span>
    {/if}
  {/each}
</div>

<style>
  .crumbs {
    max-width: 980px;
    margin: 0 auto;
    padding: 0 14px 10px;
    font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
    font-weight: 750;
    font-size: 0.92rem;
    color: #64748b;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: center;
  }

  .sep {
    color: #94a3b8;
    font-weight: 900;
  }

  .crumb {
    color: #475569;
    text-decoration: none;
    padding: 2px 6px;
    border-radius: 10px;
  }

  a.crumb:hover {
    background: #f1f5f9;
    color: #0f172a;
  }

  .current {
    color: #0f172a;
    font-weight: 900;
  }
</style>
