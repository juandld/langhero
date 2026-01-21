import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

const publicBackendUrl = (process.env.PUBLIC_BACKEND_URL || '').trim();
const allowTunnelHosts =
	process.env.ALLOW_DEV_TUNNEL_HOSTS === '1' ||
	publicBackendUrl.includes('trycloudflare.com') ||
	publicBackendUrl.includes('cloudflared');

export default defineConfig({
	plugins: [sveltekit()],
	server: allowTunnelHosts ? { allowedHosts: true } : undefined
});
