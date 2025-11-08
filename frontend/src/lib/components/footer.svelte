<script lang="ts">
	import darkMode from '$lib/stores/darkMode.svelte';
	import MailIcon from '~icons/fluent-color/mail-16';
	import GithubIcon from '~icons/logos/github-icon';
	import LL from '$i18n/i18n-svelte';
	import Dark from '~icons/material-symbols/dark-mode-outline';
	import Light from '~icons/iconamoon/mode-light';
	import Language from '~icons/material-symbols/language';
	import { slide } from 'svelte/transition';
	import { quintInOut } from 'svelte/easing';
	import type { Locales } from '$i18n/i18n-types';
	import language from '$lib/stores/language.svelte';
	import { invalidateAll } from '$app/navigation';
	import Dropdown from './dropdown.svelte';

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

<div class="fixed left-0 bottom-10 min-h-1 w-full shadow-inner shadow-black bg-background"></div>
<footer
	class="bg-inset fixed bottom-0 left-0 flex h-10 w-full flex-row items-center justify-between p-1 text-sm"
>
	<!-- Controls -->
	<section class="flex flex-row gap-2 items-center ml-2">
		<button
			class="clickable flex h-full w-fit flex-col items-center justify-center"
			onclick={() => (darkMode.enabled = !darkMode.enabled)}
			title="Enable {darkMode.enabled ? 'Light' : 'Dark'} Mode"
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
			title="Change Language"
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
	<section class="flex flex-row gap-1 items-center">
		<a
			href="https://github.com/realdegrees/text.ur/issues/new"
			target="_blank"
			rel="noreferrer noopener"
			class="h-full"
		>
			<GithubIcon />
		</a>
		<a
			href="mailto:fabian.schebera@stud.uni-regensburg.de"
			target="_blank"
			rel="noreferrer noopener"
			class="h-full"
		>
			<MailIcon />
		</a>

		<a href="https://www.uni-regensburg.de/impressum" target="_blank" rel="noreferrer noopener">
			<p class="ml-1">{$LL.imprint()}</p>
		</a>
		<p class="col-span-2 row-start-2 text-center opacity-60">
			© {new Date().getFullYear()} Universität Regensburg. All rights reserved.
		</p>
	</section>
</footer>
