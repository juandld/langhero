<script lang="ts">
  import { onMount } from 'svelte';
  import { browser } from '$app/environment';
  import { getBackendUrl } from '$lib/config';
  import { runsStore } from '$lib/runStore.js';
  import { DEVTOOLS_ENABLED } from '$lib/devtools';

  type BackendMeta = {
    demo_mode?: boolean;
    demo_video_cache_only?: boolean;
    demo_allow_llm_import?: boolean;
    demo_disable_streaming?: boolean;
    utc_now?: string;
  };

  type WeeklyUsage = {
    year?: number;
    iso_week?: number;
    updated_at?: string;
    totals?: { events?: number };
    providers?: Record<string, number>;
    events?: Record<string, number>;
    models?: Record<string, number>;
    by_event_provider_model?: Record<string, number>;
  };

  type RecentPayload = {
    limit?: number;
    days?: number;
    events?: Array<Record<string, unknown>>;
  };

  const RATES_KEY = 'LANGHERO_COST_RATES_V1';
  const OPEN_KEY = 'LANGHERO_DEVTOOLS_OPEN_V1';

  let devMode = false;
  let open = false;

  let backendUrl = '';
  let meta: BackendMeta | null = null;
  let weekly: WeeklyUsage | null = null;
  let recent: RecentPayload | null = null;

  let rates: Record<string, number> = {};
  let loading = false;
  let error = '';
  let runCount = 0;
  let lsBytes = 0;

  function loadRates() {
    if (!browser) return;
    try {
      const raw = localStorage.getItem(RATES_KEY);
      const parsed = raw ? JSON.parse(raw) : null;
      if (parsed && typeof parsed === 'object') {
        const next: Record<string, number> = {};
        for (const [k, v] of Object.entries(parsed)) {
          const n = Number(v);
          if (Number.isFinite(n) && n >= 0) next[String(k)] = n;
        }
        rates = next;
      }
    } catch (_) {}
  }

  function persistRates() {
    if (!browser) return;
    try {
      localStorage.setItem(RATES_KEY, JSON.stringify(rates));
    } catch (_) {}
  }

  function persistOpen() {
    if (!browser) return;
    try {
      localStorage.setItem(OPEN_KEY, open ? '1' : '0');
    } catch (_) {}
  }

  function parseTripKey(key: string): { event: string; provider: string; model: string } {
    const parts = String(key || '').split('|');
    const event = parts[0] || 'unknown';
    const provider = parts[1] || 'unknown';
    const model = parts.slice(2).join('|') || 'unknown';
    return { event, provider, model };
  }

  function formatMoneyUsd(value: number): string {
    const n = Number(value);
    if (!Number.isFinite(n)) return '$0.00';
    return `$${n.toFixed(4)}`.replace(/(\.\d{2})\d+$/, '$1');
  }

  function getLocalStorageBytes(keys: string[]): number {
    if (!browser) return 0;
    let total = 0;
    for (const k of keys) {
      try {
        const v = localStorage.getItem(k) || '';
        total += v.length * 2;
      } catch (_) {}
    }
    return total;
  }

  function formatBytes(n: number): string {
    const v = Number(n);
    if (!Number.isFinite(v) || v <= 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    let idx = 0;
    let x = v;
    while (x >= 1024 && idx < units.length - 1) {
      x /= 1024;
      idx += 1;
    }
    return `${x.toFixed(idx === 0 ? 0 : 1)} ${units[idx]}`;
  }

  async function refresh() {
    if (!browser) return;
    error = '';
    loading = true;
    backendUrl = getBackendUrl();
    try {
      const [metaRes, weeklyRes, recentRes] = await Promise.all([
        fetch(`${backendUrl}/api/meta`),
        fetch(`${backendUrl}/api/usage/weekly`),
        fetch(`${backendUrl}/api/usage/recent?limit=150&days=7`),
      ]);
      meta = metaRes.ok ? await metaRes.json() : null;
      weekly = weeklyRes.ok ? await weeklyRes.json() : null;
      recent = recentRes.ok ? await recentRes.json() : null;
    } catch (_) {
      error = 'Backend unreachable (or missing /api/usage endpoints).';
      meta = null;
      weekly = null;
      recent = null;
    } finally {
      loading = false;
    }
  }

  function toggle() {
    open = !open;
    persistOpen();
    if (open) refresh();
  }

  function setRate(key: string, value: string) {
    const n = Number(value);
    if (!Number.isFinite(n) || n < 0) {
      const { [key]: _, ...rest } = rates;
      rates = rest;
      persistRates();
      return;
    }
    rates = { ...rates, [key]: n };
    persistRates();
  }

  function computeTotals() {
    const triples = weekly?.by_event_provider_model || {};
    let totalEvents = 0;
    let totalCost = 0;
    for (const [k, countRaw] of Object.entries(triples)) {
      const count = Number(countRaw) || 0;
      totalEvents += count;
      const rate = Number(rates[k] ?? 0) || 0;
      totalCost += count * rate;
    }
    return { totalEvents, totalCost };
  }

  function sortedTriples(): Array<{ key: string; count: number; event: string; provider: string; model: string; rate: number; est: number }> {
    const triples = weekly?.by_event_provider_model || {};
    const out: Array<{ key: string; count: number; event: string; provider: string; model: string; rate: number; est: number }> = [];
    for (const [k, countRaw] of Object.entries(triples)) {
      const count = Number(countRaw) || 0;
      const { event, provider, model } = parseTripKey(k);
      const rate = Number(rates[k] ?? 0) || 0;
      out.push({ key: k, count, event, provider, model, rate, est: count * rate });
    }
    out.sort((a, b) => (b.est - a.est) || (b.count - a.count) || a.key.localeCompare(b.key));
    return out;
  }

  onMount(() => {
    devMode = Boolean(DEVTOOLS_ENABLED);
    if (!devMode) return;
    loadRates();
    try {
      open = localStorage.getItem(OPEN_KEY) === '1';
    } catch (_) {}
    if (open) refresh();
  });

  $: if (browser && devMode) {
    try {
      // eslint-disable-next-line no-undef
      runCount = Array.isArray($runsStore) ? $runsStore.length : 0;
    } catch (_) {
      runCount = 0;
    }
    lsBytes = getLocalStorageBytes(['LANGHERO_SAVED_RUNS_V1', 'LANGHERO_ACTIVE_RUN_ID_V1', RATES_KEY]);
  }
</script>

{#if devMode}
  <div class="dock" aria-label="Dev tools">
    <button class="toggle" type="button" on:click={toggle}>{open ? 'Close dev tools' : 'Dev tools'}</button>
    {#if open}
      <div class="panel">
        <div class="panelHead">
          <div class="title">Dev Tools</div>
          <button class="mini" type="button" disabled={loading} on:click={refresh}>{loading ? 'Loading…' : 'Refresh'}</button>
        </div>

        {#if error}
          <div class="err" role="alert">{error}</div>
        {/if}

        <div class="section">
          <div class="label">Backend</div>
          <div class="kv"><span class="k">URL</span><code class="v">{backendUrl}</code></div>
          {#if meta}
            <div class="kv"><span class="k">Demo</span><span class="v">{meta.demo_mode ? 'on' : 'off'}</span></div>
            {#if meta.demo_mode}
              <div class="kv"><span class="k">Video</span><span class="v">{meta.demo_video_cache_only ? 'cache-only' : 'normal'}</span></div>
              <div class="kv"><span class="k">LLM import</span><span class="v">{meta.demo_allow_llm_import ? 'allowed' : 'disabled'}</span></div>
              <div class="kv"><span class="k">Streaming</span><span class="v">{meta.demo_disable_streaming ? 'disabled' : 'enabled'}</span></div>
            {/if}
          {/if}
        </div>

        <div class="section">
          <div class="label">Weekly Usage (Estimated)</div>
          {#if weekly?.by_event_provider_model}
            {@const totals = computeTotals()}
            <div class="totals">
              <div><span class="k">Events</span> <span class="v">{totals.totalEvents}</span></div>
              <div><span class="k">Est. cost</span> <span class="v">{formatMoneyUsd(totals.totalCost)}</span></div>
            </div>
            <div class="hint">
              Set unit prices per <code>event|provider|model</code> to estimate cost. Defaults are 0.
            </div>
            <div class="table">
              <div class="row head">
                <div>Event</div>
                <div>Provider</div>
                <div>Model</div>
                <div class="num">Count</div>
                <div class="num">Unit $</div>
                <div class="num">Est $</div>
              </div>
              {#each sortedTriples().slice(0, 25) as row (row.key)}
                <div class="row">
                  <div class="mono">{row.event}</div>
                  <div class="mono">{row.provider}</div>
                  <div class="mono">{row.model}</div>
                  <div class="num">{row.count}</div>
                  <div class="num">
                    <input
                      class="rate"
                      type="number"
                      min="0"
                      step="0.0001"
                      value={rates[row.key] ?? ''}
                      placeholder="0"
                      on:input={(e) => setRate(row.key, (e.currentTarget as HTMLInputElement).value)}
                    />
                  </div>
                  <div class="num">{formatMoneyUsd(row.est)}</div>
                </div>
              {/each}
            </div>
            {#if Object.keys(weekly.by_event_provider_model).length > 25}
              <div class="hint">Showing top 25 by estimated cost. Adjust unit prices to change ordering.</div>
            {/if}
          {:else}
            <div class="hint">No weekly usage data yet.</div>
          {/if}
        </div>

        <div class="section">
          <div class="label">Recent Usage</div>
          {#if Array.isArray(recent?.events) && recent.events.length}
            <ul class="recent">
              {#each recent.events.slice(0, 25) as evt, i (i)}
                <li>
                  <code>{String(evt.event ?? '')}</code>
                  <span class="mono">{String(evt.provider ?? '')}</span>
                  <span class="mono">{String(evt.model ?? '')}</span>
                  {#if evt.status}<span class="mono">{String(evt.status ?? '')}</span>{/if}
                </li>
              {/each}
            </ul>
          {:else}
            <div class="hint">No recent events yet.</div>
          {/if}
        </div>

        <div class="section">
          <div class="label">Local</div>
          <div class="kv"><span class="k">Runs</span><span class="v">{runCount}</span></div>
          <div class="kv"><span class="k">localStorage</span><span class="v">{formatBytes(lsBytes)} (approx)</span></div>
        </div>
      </div>
    {/if}
  </div>
{/if}

<style>
  .dock {
    position: fixed;
    right: 16px;
    bottom: 16px;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    gap: 10px;
    align-items: flex-end;
    font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
  }

  .toggle {
    background: #111827;
    color: #fff;
    border: none;
    border-radius: 999px;
    padding: 10px 12px;
    cursor: pointer;
    font-weight: 900;
    box-shadow: 0 10px 26px rgba(15, 23, 42, 0.35);
  }

  .panel {
    width: min(720px, calc(100vw - 32px));
    max-height: min(78vh, 720px);
    overflow: auto;
    background: #0b1220;
    color: #e2e8f0;
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 18px;
    padding: 14px;
    box-shadow: 0 18px 50px rgba(15, 23, 42, 0.55);
  }

  .panelHead {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
  }

  .title {
    font-weight: 950;
    letter-spacing: -0.02em;
  }

  .mini {
    background: rgba(255, 255, 255, 0.08);
    color: #e2e8f0;
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 12px;
    padding: 8px 10px;
    cursor: pointer;
    font-weight: 850;
  }

  .mini:disabled {
    opacity: 0.65;
    cursor: not-allowed;
  }

  .err {
    background: rgba(239, 68, 68, 0.12);
    border: 1px solid rgba(248, 113, 113, 0.45);
    border-radius: 14px;
    padding: 10px 12px;
    color: #fecaca;
    font-weight: 850;
    margin-bottom: 10px;
  }

  .section {
    border-top: 1px solid rgba(148, 163, 184, 0.18);
    padding-top: 12px;
    margin-top: 12px;
  }

  .label {
    font-weight: 900;
    text-transform: uppercase;
    font-size: 0.82rem;
    letter-spacing: 0.08em;
    color: #cbd5e1;
    margin-bottom: 8px;
  }

  .kv {
    display: flex;
    gap: 10px;
    align-items: baseline;
    margin-bottom: 4px;
    flex-wrap: wrap;
  }

  .kv .k {
    font-weight: 900;
    color: #93c5fd;
    min-width: 92px;
  }

  .kv .v {
    font-weight: 750;
    color: #e2e8f0;
  }

  code {
    background: rgba(148, 163, 184, 0.12);
    border: 1px solid rgba(148, 163, 184, 0.18);
    padding: 2px 6px;
    border-radius: 8px;
  }

  .hint {
    color: #cbd5e1;
    font-weight: 650;
    font-size: 0.9rem;
    margin-top: 6px;
  }

  .totals {
    display: flex;
    gap: 14px;
    flex-wrap: wrap;
    margin-bottom: 6px;
    font-weight: 850;
  }

  .totals .k {
    color: #93c5fd;
    font-weight: 900;
  }

  .totals .v {
    color: #e2e8f0;
  }

  .table {
    margin-top: 10px;
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: 14px;
    overflow: hidden;
  }

  .row {
    display: grid;
    grid-template-columns: 1.1fr 0.8fr 1.2fr 0.5fr 0.6fr 0.6fr;
    gap: 10px;
    padding: 8px 10px;
    align-items: center;
    border-top: 1px solid rgba(148, 163, 184, 0.12);
  }

  .row.head {
    background: rgba(255, 255, 255, 0.04);
    border-top: none;
    font-weight: 950;
    color: #e2e8f0;
  }

  .mono {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    font-size: 0.9rem;
  }

  .num {
    text-align: right;
    font-variant-numeric: tabular-nums;
    font-feature-settings: "tnum";
  }

  .rate {
    width: 90px;
    text-align: right;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 10px;
    color: #e2e8f0;
    padding: 6px 8px;
    font-weight: 800;
  }

  .recent {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
    max-height: 180px;
    overflow: auto;
  }

  .recent li {
    display: flex;
    gap: 8px;
    align-items: baseline;
    flex-wrap: wrap;
    color: #e2e8f0;
    font-weight: 700;
  }
</style>
