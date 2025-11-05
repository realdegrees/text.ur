<script lang="ts">
	import AppLogoDark from '$lib/images/logo/logo_dark.svg';
	import AppLogoLight from '$lib/images/logo/logo_light.svg';
	import darkMode from '$lib/stores/darkMode.svelte';
	import { loadingBar } from '$lib/stores/loadingBar.svelte';

	import Dark from '~icons/material-symbols/dark-mode-outline';
	import Light from '~icons/iconamoon/mode-light';
	import { scale, slide } from 'svelte/transition';
	import { cubicOut, quintInOut } from 'svelte/easing';
	import type { UserPrivate } from '$api/types';
	import ProfileImageFallback from '~icons/material-symbols/account-box';
	import Login from './login.svelte';

	let { user }: { user?: UserPrivate } = $props();
</script>

<div class="fixed top-0 right-0 left-0 z-50 h-2 bg-background"></div>
<!--TODO Can potentially be used as a subtle loading bar-->
<header
	class="center-content shadow-inner-sym-[10px] fixed top-2 right-0 left-0 z-50 grid h-16 grid-cols-3 items-center
	overflow-hidden bg-inset shadow-black dark:shadow-inner-sym-10"
>
	<a
		href="/"
		class="col-span-1 col-start-1 flex flex-row justify-self-start transition-all hover:pl-2"
	>
		<img class="w-auto p-2" src={darkMode.enabled ? AppLogoLight : AppLogoDark} alt="Logo" />
		<p class="ml-1 self-center text-3xl">text.ur</p>
	</a>

	<div class="col-span-1 col-start-3 mr-3 flex flex-row-reverse items-center justify-self-end">
		{#if user?.id}
			<a href="/users/{user.username}" class="flex w-full flex-row items-center">
				<ProfileImageFallback class="h-9 w-9" />
				<!--TODO insert user profile image if that feature is added-->
				<p class="ml-1 font-semibold">
					{user.first_name && user.last_name
						? `${user.first_name} ${user.last_name}`
						: user.username}
				</p>
			</a>
		{:else}
			<Login />
		{/if}

		<hr class="mx-4 h-9 w-1 rounded-full bg-text opacity-25" />

		<button
			class="flex h-full w-fit clickable flex-col items-center justify-center"
			onclick={() => (darkMode.enabled = !darkMode.enabled)}
			title="Enable {darkMode.enabled ? 'Light' : 'Dark'} Mode"
		>
			{#if darkMode.enabled}
				<div transition:slide={{ easing: quintInOut, duration: 500 }}>
					<Dark class="h-full w-7" />
				</div>
			{:else}
				<div transition:slide={{ easing: quintInOut, duration: 500 }}>
					<Light class="h-full w-7" />
				</div>
			{/if}
		</button>
	</div>
</header>

{#if loadingBar.visible}
	<div
		class="fixed top-18 right-0 left-0 z-60 h-[3px] origin-left rounded-full bg-primary"
		style="width: {loadingBar.progress}%"
		transition:scale={{ duration: 300, easing: cubicOut }}
	></div>
{/if}

<style lang="postcss">
	@reference '../../app.css';

	header * {
		@apply max-h-16;
	}
	a {
		@apply text-center;
	}
</style>
