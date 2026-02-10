<script lang="ts">
  import { page } from '$app/stores';
  import Breadcrumbs from '$lib/components/Breadcrumbs.svelte';
  import ProfileBadge from '$lib/components/ProfileBadge.svelte';

  const links = [
    { href: '/', label: 'Menu' },
    { href: '/import', label: 'Import' },
    { href: '/demo', label: 'Demo' },
    { href: '/login', label: 'Login' },
  ];

  $: path = $page?.url?.pathname || '/';
  function isActive(href: string) {
    if (href === '/') return path === '/';
    return path === href || path.startsWith(`${href}/`);
  }
</script>

<header class="topnav">
  <div class="inner">
    <a class="brand" href="/" aria-label="LangHero menu">LangHero</a>
    <div class="profile-section">
      <ProfileBadge compact />
    </div>
    <nav class="nav" aria-label="Primary">
      {#each links as l (l.href)}
        <a class={`link ${isActive(l.href) ? 'active' : ''}`} href={l.href}>{l.label}</a>
      {/each}
    </nav>
  </div>
  <Breadcrumbs />
</header>

<style>
  .topnav {
    position: sticky;
    top: 0;
    z-index: 9000;
    background: rgba(255, 255, 255, 0.92);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid #e2e8f0;
  }

  .inner {
    max-width: 980px;
    margin: 0 auto;
    padding: 10px 14px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
  }

  .brand {
    color: #0f172a;
    text-decoration: none;
    font-weight: 950;
    letter-spacing: -0.02em;
    padding: 8px 10px;
    border-radius: 12px;
  }

  .brand:hover {
    background: #f8fafc;
  }

  .profile-section {
    flex: 1;
    display: flex;
    justify-content: center;
  }

  .nav {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .link {
    color: #0f172a;
    text-decoration: none;
    font-weight: 850;
    padding: 8px 10px;
    border-radius: 12px;
    border: 1px solid transparent;
  }

  .link:hover {
    background: #f8fafc;
    border-color: #e2e8f0;
  }

  .link.active {
    background: #0f172a;
    color: #fff;
    border-color: #0f172a;
  }
</style>
