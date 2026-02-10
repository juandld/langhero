<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import DevToolsDock from '$lib/components/DevToolsDock.svelte';
  import TopNav from '$lib/components/TopNav.svelte';
  import { hydrateAuth } from '$lib/auth';
  import { profileStore } from '$lib/profileStore';

  onMount(() => {
    hydrateAuth();
    profileStore.hydrate();
  });

  // Hide nav on immersive routes (main menu, story mode, gameplay)
  $: isImmersiveRoute = (() => {
    const path = $page?.url?.pathname || '';
    return path === '/' || path === '/story' || path.startsWith('/play/') || path === '/demo' || path === '/learn';
  })();
</script>

{#if !isImmersiveRoute}
  <TopNav />
{/if}
<slot />
{#if !isImmersiveRoute}
  <DevToolsDock />
{/if}
