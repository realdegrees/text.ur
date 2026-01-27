import { mdsvex } from 'mdsvex';
import adapter from '@sveltejs/adapter-node';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	// Consult https://svelte.dev/docs/kit/integrations
	// for more information about preprocessors
	preprocess: [vitePreprocess(), mdsvex()],
	kit: {
		// adapter-auto only supports some environments, see https://svelte.dev/docs/kit/adapter-auto for a list.
		// If your environment is not supported, or you settled on a specific environment, switch out the adapter.
		// See https://svelte.dev/docs/kit/adapters for more information about adapters.
		adapter: adapter(),
		csp: {
			mode: 'auto',
			directives: {
				'default-src': ['self'],
				'script-src': ['self'],
				'style-src': ['self', 'unsafe-inline'],
				'connect-src': process.env.NODE_ENV === 'development'
					? ['self', 'wss:', 'ws:', 'http:', 'https:', 'blob:']
					: ['self', 'wss:', 'https:', 'blob:'],
				'img-src': ['self', 'data:', 'blob:'],
				'worker-src': ['self', 'blob:'],
				'object-src': ['none'],
				'base-uri': ['self'],
				'form-action': ['self'],
				'frame-ancestors': ['none']
			}
		},
		alias: {
			'$api/*': './src/api/*',
			'$types/*': './src/types/*',
			'$i18n/*': './src/i18n/*'
		},
		env: {
			dir: '..'
		}
	},
	extensions: ['.svelte', '.svx']
};

export default config;
