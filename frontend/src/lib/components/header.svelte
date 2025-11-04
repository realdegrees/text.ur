<script lang="ts">
	import AppLogoDark from '$lib/images/logo/logo_dark.svg';
	import AppLogoLight from '$lib/images/logo/logo_light.svg';
	import darkMode from '$lib/darkMode.svelte';

	import Dark from '~icons/material-symbols/dark-mode-outline';
	import Light from '~icons/iconamoon/mode-light';
	import { slide } from 'svelte/transition';
	import { quintInOut } from 'svelte/easing';
	import type { UserPrivate } from '$api/types';
	import ProfileImageFallback from '~icons/material-symbols/account-box';
	import Login from './login.svelte';

	interface Props {
		user?: UserPrivate;
	}

	let { user }: Props = $props();
</script>

<div class="fixed top-0 h-2 left-0 right-0 z-50 bg-background"></div>
<!--TODO Can potentially be used as a subtle loading bar-->
<header
	class="fixed top-2 left-0 right-0 h-16 z-50 overflow-hidden grid items-center grid-cols-3 center-content
	bg-inset shadow-inner-sym-[10px] dark:shadow-inner-sym-10 shadow-black"
>
	<a
		href="/"
		class="flex flex-row justify-self-start col-start-1 col-span-1 hover:pl-2 transition-all"
	>
		<img
			class="w-auto p-2"
			src={darkMode.enabled ? AppLogoLight : AppLogoDark}
			alt="Logo"
		/>
		<p class="ml-1 text-3xl self-center">text.ur</p>
	</a>

	<div class="flex flex-row-reverse items-center mr-3 justify-self-end col-start-3 col-span-1">
		{#if user?.id}
			<a href="/users/{user.username}" class="w-full flex flex-row items-center">
				<ProfileImageFallback class="h-9 w-9" />
				<!--TODO insert user profile image if that feature is added-->
				<p class="ml-1 font-semibold">
					{(user.first_name && user.last_name)
						? `${user.first_name} ${user.last_name}`
						: user.username}
				</p>
			</a>
		{:else}
			<Login />
		{/if}

		<hr class="rounded-full bg-text opacity-25 w-1 mx-4 h-9" />

		<button
			class="h-full w-fit clickable flex flex-col justify-center items-center"
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

<style lang="postcss">
	@reference '../../app.css';

	header * {
		@apply max-h-16;
	}
	a {
		@apply text-center;
	}
</style>
