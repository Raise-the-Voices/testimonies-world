import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		allowedHosts: ['demos.linkedtrust.us', 'localhost', '127.0.0.1', 'cases.raisethevoices.org'],
		proxy: {
			// Proxy API calls to the live backend at cases.raisethevoices.org.
			// We use the live API here (not local Django) because the local
			// Postgres credentials in .env are placeholders that don't
			// authenticate against 10.0.0.100. Server-to-server requests have
			// no CORS restrictions, so this works fine for dev.
			//
			// For an offline dev setup, switch the target to
			// 'http://127.0.0.1:8040' and start Django with USE_SQLITE=True.
			'/testimonies/api': {
				target: 'https://cases.raisethevoices.org',
				changeOrigin: true,
				secure: true,
				rewrite: (path) => path.replace(/^\/testimonies\/api/, '/api'),
			},
		},
	}
});
