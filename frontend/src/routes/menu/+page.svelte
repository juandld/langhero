<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';

  onMount(() => {
    goto('/');
  });
</script>

<main style="font-family: sans-serif; max-width: 760px; margin: 0 auto; padding: 2rem 1.25rem;">
  <h1>Redirecting…</h1>
  <p><a href="/">Go to menu</a></p>
</main>

