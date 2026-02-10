<script>
  /**
   * AestheticProvider - Provides visual theme context for story components.
   *
   * Two modes:
   * - 'holographic': Future/simulation aesthetic (tutorial, intro)
   * - 'cinematic': Past/real stakes aesthetic (main story)
   */
  import { setContext, onMount } from 'svelte';
  import { writable } from 'svelte/store';
  import '$lib/styles/aesthetics.css';

  export let mode = 'holographic'; // 'holographic' | 'cinematic'

  // Create a writable store for the aesthetic mode
  const aesthetic = writable(mode);

  // Update store when prop changes
  $: aesthetic.set(mode);

  // Provide context for child components
  setContext('aesthetic', aesthetic);

  // Track for visual effects
  let showScanLines = false;
  let showFilmGrain = false;
  let showGridOverlay = false;

  $: {
    showScanLines = mode === 'holographic';
    showFilmGrain = mode === 'cinematic';
    showGridOverlay = mode === 'holographic';
  }

  // Check for reduced motion preference
  let prefersReducedMotion = false;

  onMount(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    prefersReducedMotion = mediaQuery.matches;

    const handler = (e) => {
      prefersReducedMotion = e.matches;
    };

    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  });
</script>

<div class="aesthetic-provider" data-aesthetic={mode}>
  <!-- Visual effect overlays -->
  {#if showScanLines && !prefersReducedMotion}
    <div class="scan-lines" aria-hidden="true"></div>
  {/if}

  {#if showGridOverlay && !prefersReducedMotion}
    <div class="holo-grid-overlay" aria-hidden="true"></div>
  {/if}

  {#if showFilmGrain && !prefersReducedMotion}
    <div class="film-grain" aria-hidden="true"></div>
  {/if}

  <!-- Content slot -->
  <slot />
</div>

<style>
  .aesthetic-provider {
    position: relative;
    width: 100%;
    height: 100%;
    min-height: 100vh;
    min-height: 100dvh;
    transition: background-color 0.5s ease;
  }

  /* Holographic background */
  [data-aesthetic="holographic"].aesthetic-provider {
    background: linear-gradient(135deg,
      var(--aesthetic-bg-primary) 0%,
      var(--aesthetic-bg-secondary) 50%,
      var(--aesthetic-bg-tertiary) 100%
    );
  }

  /* Cinematic background */
  [data-aesthetic="cinematic"].aesthetic-provider {
    background: linear-gradient(135deg,
      var(--aesthetic-bg-primary) 0%,
      var(--aesthetic-bg-secondary) 50%,
      var(--aesthetic-bg-tertiary) 100%
    );
  }
</style>
