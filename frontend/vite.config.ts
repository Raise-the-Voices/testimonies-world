import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		allowedHosts: ['demos.linkedtrust.us', 'localhost', '127.0.0.1'],
	}
});
