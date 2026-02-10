<script lang="ts">
  import { onMount } from 'svelte';
  import { getBackendUrl } from '$lib/config';
  import { apiFetch } from '$lib/api';

  type BackendMeta = {
    demo_mode?: boolean;
    demo_video_cache_only?: boolean;
    demo_allow_llm_import?: boolean;
    demo_disable_streaming?: boolean;
    utc_now?: string;
  };

  export let compact = false;

  let meta: BackendMeta | null = null;
  let error = '';

  onMount(async () => {
    error = '';
    try {
      const res = await apiFetch(`${getBackendUrl()}/api/meta`);
      if (!res.ok) return;
      const data = await res.json();
      if (data && typeof data === 'object') meta = data;
    } catch (_) {
      error = 'unreachable';
    }
  });
</script>

{#if meta?.demo_mode}
  <div class={`banner ${compact ? 'compact' : ''}`} role="status" aria-live="polite">
    <strong>Demo mode:</strong>
    {#if meta?.demo_video_cache_only}
      <span>video imports require cache hits</span>
    {/if}
    {#if meta?.demo_disable_streaming}
      <span>· live streaming disabled</span>
    {/if}
    {#if meta?.demo_allow_llm_import === false}
      <span>· story imports use deterministic fallback</span>
    {/if}
  </div>
{/if}

<style>
  .banner {
    border: 1px solid #fed7aa;
    background: #fff7ed;
    color: #7c2d12;
    border-radius: 14px;
    padding: 10px 12px;
    font-weight: 800;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
  }
  .compact {
    padding: 8px 10px;
    border-radius: 12px;
    font-weight: 750;
    font-size: 0.9rem;
  }
</style>
