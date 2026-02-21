<script lang="ts">
	import darkMode from '$lib/stores/darkMode.svelte';
	import MailIcon from '~icons/fluent-color/mail-16';
	import GithubIcon from '~icons/logos/github-icon';
	import SvelteIcon from '~icons/vscode-icons/file-type-svelte';
	import LL from '$i18n/i18n-svelte';
	import Dark from '~icons/material-symbols/dark-mode-outline';
	import Light from '~icons/iconamoon/mode-light';
	import Language from '~icons/material-symbols/language';
	import { slide } from 'svelte/transition';
	import { quintInOut } from 'svelte/easing';
	import type { Locales } from '$i18n/i18n-types';
	import language from '$lib/stores/language.svelte';
	import { invalidateAll } from '$app/navigation';
	import Dropdown from '../lib/components/dropdown.svelte';

	let currentLanguage = $derived(language.locale);

	const languageNames: Record<Locales, string> = {
		en: 'English',
		de: 'Deutsch'
	};

	async function changeLanguage(locale: Locales) {
		// Set the language using the store
		language.setLocale(locale);

		// Invalidate all data to trigger +layout.ts reload
		await invalidateAll();
	}
</script>

<div class="h-11 w-full"></div>
<div
	class="fixed bottom-10 left-0 z-40 min-h-1 w-full bg-background shadow-inner shadow-black/80"
></div>
<footer
	class="fixed bottom-0 left-0 z-40 flex h-10 w-full flex-row items-center justify-between bg-inset p-1 text-sm"
>
	<!-- Controls -->
	<section class="ml-2 flex flex-row items-center gap-2">
		<button
			class="flex h-full w-fit clickable flex-col items-center justify-center"
			onclick={() => (darkMode.enabled = !darkMode.enabled)}
			title={darkMode.enabled ? $LL.footer.enableLightMode() : $LL.footer.enableDarkMode()}
		>
			{#if darkMode.enabled}
				<div transition:slide={{ easing: quintInOut, duration: 500 }}>
					<Dark />
				</div>
			{:else}
				<div transition:slide={{ easing: quintInOut, duration: 500 }}>
					<Light />
				</div>
			{/if}
		</button>
		<!-- Language Selector -->
		<Dropdown
			items={language.availableLocales}
			bind:currentItem={currentLanguage}
			itemTextMap={(locale) => languageNames[locale]}
			onSelect={changeLanguage}
			position="top-left"
			title={$LL.footer.changeLanguage()}
		>
			{#snippet icon()}
				<Language class="h-full" />
			{/snippet}

			{#snippet itemSnippet(locale)}
				<p class="p-1 text-left">{languageNames[locale]}</p>
			{/snippet}
		</Dropdown>
	</section>

	<!-- Links -->
	<section class="flex flex-row items-center gap-1">
		<span class="mr-2 flex items-center gap-1 text-xs text-text/60">
			{$LL.builtWith()}
			<SvelteIcon class="h-4 w-4" />
		</span>
		<a
			href="https://github.com/realdegrees/text.ur"
			target="_blank"
			rel="noreferrer noopener"
			class="h-full"
		>
			<GithubIcon />
		</a>
		<a
			href="mailto:Text.ur@sprachlit.uni-regensburg.de"
			target="_blank"
			rel="noreferrer noopener"
			class="h-full"
		>
			<MailIcon />
		</a>

		<a
			href={language.locale === 'de'
				? 'https://www.uni-regensburg.de/impressum'
				: 'https://www.uni-regensburg.de/en/legal-notice'}
			target="_blank"
			rel="noreferrer noopener"
		>
			<p class="ml-1">{$LL.imprint()}</p>
		</a>
		<p class="col-span-2 row-start-2 text-center opacity-60">
			© {new Date().getFullYear()} Universität Regensburg
		</p>
	</section>
</footer>
