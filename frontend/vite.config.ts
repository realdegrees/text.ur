import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vitest/config';
import Icons from 'unplugin-icons/vite';

export default defineConfig({
	plugins: [
		tailwindcss(), 
		sveltekit(),
		Icons({
			compiler: 'svelte',
			defaultClass: 'icon'
		})
	],
	test: {
		coverage: {
			include: ['src/**/*.ts', 'src/**/*.svelte'],
			exclude: ['src/api/**/*', 'src/i18n/**/*'],
			reporter: ['text', 'html']
		}
	},
	resolve: process.env.VITEST
		? {
				conditions: ['browser']
			}
		: undefined
});
