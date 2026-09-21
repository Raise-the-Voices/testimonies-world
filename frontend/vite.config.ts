import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

// VITE_API_PROXY_TARGET overrides where the dev server proxies
// /testimonies/api/* requests. When unset, requests go to the live
// production backend (cases.raisethevoices.org) — the default for
// day-to-day dev, since the local Postgres credentials in .env are
// placeholders that don't authenticate against 10.0.0.100.
//
// The Playwright E2E suite sets this to http://127.0.0.1:8040 so
// specs run against the local backend and the /__test__/login/
// bootstrap (see backend/cases/test_auth.py) actually exercises
// the code under test instead of a production data plane.
const proxyTarget = process.env.VITE_API_PROXY_TARGET ?? 'https://cases.raisethevoices.org';
const proxyIsHttps = proxyTarget.startsWith('https://');

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		allowedHosts: ['demos.linkedtrust.us', 'localhost', '127.0.0.1', 'cases.raisethevoices.org'],
		proxy: {
			'/testimonies/api': {
				target: proxyTarget,
				changeOrigin: true,
				secure: proxyIsHttps,
				rewrite: (path) => path.replace(/^\/testimonies\/api/, '/api'),
			},
			'/testimonies/accounts/': {
				target: proxyTarget,
				changeOrigin: true,
				secure: proxyIsHttps,
				rewrite: (path) => path.replace(/^\/testimonies\/accounts', '/accounts'),
			},
		},
	}
});
