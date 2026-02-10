<script>
  import { onMount } from 'svelte';
  import { fade, fly } from 'svelte/transition';
  import { getApiBase } from '$lib/api';

  const API_BASE = getApiBase();

  let stories = [];
  let loading = true;
  let error = null;

  onMount(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/story-panels/stories`);
      if (!res.ok) throw new Error('Failed to load stories');
      const data = await res.json();
      stories = data.stories || [];
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });
</script>

<div class="stories-page">
  <header class="header">
    <h1>Stories</h1>
    <p class="subtitle">Choose your adventure</p>
  </header>

  {#if loading}
    <div class="loading">
      <div class="spinner"></div>
      <p>Loading stories...</p>
    </div>
  {:else if error}
    <div class="error">{error}</div>
  {:else if stories.length === 0}
    <div class="empty">No stories available yet.</div>
  {:else}
    <div class="stories-grid">
      {#each stories as story, i}
        <a
          href="/play/story/{story.id}"
          class="story-card"
          in:fly={{ y: 20, delay: i * 100, duration: 400 }}
        >
          <div class="story-badge">{story.chapter_count} chapters</div>
          <h2 class="story-title">{story.title}</h2>
          {#if story.subtitle}
            <p class="story-subtitle">{story.subtitle}</p>
          {/if}
          <div class="story-action">
            Start Journey →
          </div>
        </a>
      {/each}
    </div>
  {/if}
</div>

<style>
  .stories-page {
    min-height: 100vh;
    background: linear-gradient(135deg, #0f0a1a 0%, #1a0a2e 50%, #0a1628 100%);
    padding: 2rem 1rem;
    font-family: 'Segoe UI', system-ui, sans-serif;
  }

  .header {
    text-align: center;
    margin-bottom: 3rem;
  }

  h1 {
    font-size: 2.5rem;
    font-weight: 800;
    color: #fff;
    margin: 0 0 0.5rem 0;
    background: linear-gradient(135deg, #a855f7, #06b6d4);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .subtitle {
    color: #71717a;
    font-size: 1.1rem;
    margin: 0;
  }

  .loading, .error, .empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 50vh;
    color: #a1a1aa;
    gap: 1rem;
  }

  .error {
    color: #ef4444;
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 3px solid #333;
    border-top-color: #a855f7;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .stories-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1.5rem;
    max-width: 1200px;
    margin: 0 auto;
  }

  .story-card {
    position: relative;
    display: flex;
    flex-direction: column;
    padding: 2rem;
    background: linear-gradient(135deg, rgba(30, 20, 50, 0.8), rgba(20, 30, 50, 0.8));
    border: 1px solid rgba(139, 92, 246, 0.3);
    border-radius: 16px;
    text-decoration: none;
    color: #fff;
    transition: all 0.3s ease;
    overflow: hidden;
  }

  .story-card::before {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(6, 182, 212, 0.1));
    opacity: 0;
    transition: opacity 0.3s ease;
  }

  .story-card:hover {
    transform: translateY(-4px);
    border-color: rgba(139, 92, 246, 0.6);
    box-shadow: 0 20px 40px rgba(139, 92, 246, 0.2);
  }

  .story-card:hover::before {
    opacity: 1;
  }

  .story-badge {
    position: absolute;
    top: 1rem;
    right: 1rem;
    padding: 0.25rem 0.75rem;
    background: rgba(139, 92, 246, 0.3);
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    color: #c4b5fd;
  }

  .story-title {
    font-size: 1.5rem;
    font-weight: 700;
    margin: 0 0 0.5rem 0;
    color: #fff;
    position: relative;
  }

  .story-subtitle {
    font-size: 0.95rem;
    color: #a1a1aa;
    margin: 0 0 1.5rem 0;
    position: relative;
  }

  .story-action {
    margin-top: auto;
    padding-top: 1rem;
    font-weight: 600;
    color: #a78bfa;
    position: relative;
    transition: color 0.2s ease;
  }

  .story-card:hover .story-action {
    color: #c4b5fd;
  }

  @media (max-width: 640px) {
    .stories-page {
      padding: 1.5rem 1rem;
    }

    h1 {
      font-size: 2rem;
    }

    .stories-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
