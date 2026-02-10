<script lang="ts">
  import { onMount } from 'svelte';
  import { authUser, completeMagicLink, isAppwriteConfigured, logout, requestMagicLink } from '$lib/auth';

  let email = '';
  let status: 'idle' | 'sending' | 'sent' | 'verifying' | 'done' | 'error' = 'idle';
  let error = '';
  let info = '';
  let configured = isAppwriteConfigured();

  async function sendLink() {
    error = '';
    info = '';
    status = 'sending';
    try {
      await requestMagicLink(email);
      status = 'sent';
      info = 'Check your email for the magic link.';
    } catch (err) {
      status = 'error';
      error = err instanceof Error ? err.message : 'Failed to send magic link.';
    }
  }

  async function verifyFromUrl() {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams(window.location.search);
    const userId = params.get('userId') || params.get('user_id');
    const secret = params.get('secret');
    if (!userId || !secret) return;
    status = 'verifying';
    error = '';
    info = 'Verifying magic link...';
    try {
      await completeMagicLink(userId, secret);
      status = 'done';
      info = 'You are signed in.';
      window.history.replaceState({}, document.title, window.location.pathname);
    } catch (err) {
      status = 'error';
      error = err instanceof Error ? err.message : 'Failed to verify magic link.';
    }
  }

  onMount(() => {
    configured = isAppwriteConfigured();
    void verifyFromUrl();
  });
</script>

<section class="login">
  <div class="card">
    <h1>Login</h1>
    {#if !configured}
      <p class="notice">Appwrite is not configured. Set `PUBLIC_APPWRITE_ENDPOINT` and `PUBLIC_APPWRITE_PROJECT_ID`.</p>
    {:else}
      {#if $authUser}
        <div class="user">
          <div class="label">Signed in as</div>
          <div class="value">{($authUser.name || $authUser.email)}</div>
          <button class="secondary" on:click={logout}>Sign out</button>
        </div>
      {:else}
        <p class="hint">Enter your email and we’ll send you a magic link.</p>
        <form class="form" on:submit|preventDefault={sendLink}>
          <label>
            Email
            <input type="email" bind:value={email} placeholder="you@example.com" required />
          </label>
          <button type="submit" disabled={status === 'sending' || status === 'verifying'}>
            {status === 'sending' ? 'Sending…' : 'Send magic link'}
          </button>
        </form>
      {/if}
      {#if info}
        <p class="info">{info}</p>
      {/if}
      {#if error}
        <p class="error">{error}</p>
      {/if}
    {/if}
  </div>
</section>

<style>
  .login {
    display: flex;
    justify-content: center;
    padding: 40px 16px;
  }

  .card {
    width: min(460px, 100%);
    background: #fff;
    border-radius: 16px;
    padding: 24px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
  }

  h1 {
    margin: 0 0 12px;
    font-size: 26px;
  }

  .hint {
    margin: 0 0 16px;
    color: #475569;
  }

  .form {
    display: grid;
    gap: 12px;
  }

  label {
    display: grid;
    gap: 6px;
    font-weight: 600;
    color: #0f172a;
  }

  input {
    border: 1px solid #cbd5f5;
    border-radius: 12px;
    padding: 10px 12px;
    font-size: 15px;
  }

  button {
    background: #0f172a;
    color: #fff;
    border: none;
    padding: 10px 14px;
    border-radius: 12px;
    font-weight: 700;
    cursor: pointer;
  }

  button[disabled] {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .secondary {
    margin-top: 12px;
    background: #fff;
    color: #0f172a;
    border: 1px solid #cbd5f5;
  }

  .notice {
    color: #7c2d12;
    background: #ffedd5;
    padding: 10px 12px;
    border-radius: 12px;
  }

  .info {
    margin-top: 12px;
    color: #1e3a8a;
  }

  .error {
    margin-top: 12px;
    color: #b91c1c;
  }

  .user {
    display: grid;
    gap: 6px;
  }

  .label {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #64748b;
  }

  .value {
    font-size: 16px;
    font-weight: 700;
  }
</style>
