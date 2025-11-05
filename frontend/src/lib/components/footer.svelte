<script lang="ts">
	import AppLogoDark from '$lib/images/logo/logo_dark.svg';
	import AppLogoLight from '$lib/images/logo/logo_light.svg';
	import URLogoDark from '$lib/images/ur/ur-logo-dark.webp';
	import URLogoLight from '$lib/images/ur/ur-logo-light.webp';

	import darkMode from '$lib/stores/darkMode.svelte';
	import MailIcon from '~icons/fluent-color/mail-16';
	import GithubIcon from '~icons/logos/github-icon';
	import LL from '$i18n/i18n-svelte';
</script>

<footer class="center-content my-2 grid w-full items-start justify-center gap-x-28">
	<!-- Generics -->
	<section class="col-start-1">
		<p class="mb-2 text-xl! font-semibold">Info</p>

		<a href="https://github.com/realdegrees/text.ur" target="_blank" rel="noreferrer noopener">
			<GithubIcon />
			<p class="ml-1">GitHub Repository</p>
		</a>

		<a href="https://www.uni-regensburg.de/impressum" target="_blank" rel="noreferrer noopener">
			<img src={darkMode.enabled ? URLogoLight : URLogoDark} alt="logo" class="h-6 w-auto" />
			<p class="ml-1">{$LL.imprint()}</p>
		</a>
	</section>

	<!-- Contact -->
	<section class="col-start-2">
		<p class="mb-2 text-xl! font-semibold">{$LL.contact()}</p>

		<a
			href="mailto:fabian.schebera@stud.uni-regensburg.de"
			target="_blank"
			rel="noreferrer noopener"
		>
			<MailIcon />
			<p class="ml-1">Email</p>
		</a>

		<a
			href="https://github.com/realdegrees/text.ur/issues/new"
			target="_blank"
			rel="noreferrer noopener"
		>
			<GithubIcon />
			<p class="ml-1">GitHub Issues</p>
		</a>
	</section>

	<p class="col-span-2 row-start-2 mt-6 text-center text-sm! opacity-60">
		© {new Date().getFullYear()} Universität Regensburg. All rights reserved.
	</p>
</footer>

<style lang="postcss">
	@reference '../../app.css';

	section *:not(.heading *) {
		@apply col-span-1 row-span-1 flex flex-col items-center self-start;
	}
	a,
	p {
		@apply text-lg;
	}
	a:has(*:not(:only-child)) {
		@apply flex flex-row items-center hover:scale-105;
	}
</style>
