<script lang="ts">
	import AppLogoDark from '$lib/images/logo/logo_dark.svg';
	import AppLogoLight from '$lib/images/logo/logo_light.svg';
	import darkMode from '$lib/stores/darkMode.svelte';
	import { loadingBar } from '$lib/stores/loadingBar.svelte';

	import { scale } from 'svelte/transition';
	import { cubicOut } from 'svelte/easing';
	import type { UserPrivate } from '$api/types';
	import ProfileImageFallback from '~icons/material-symbols/account-box';
	import Login from './login.svelte';

	let { user }: { user?: UserPrivate } = $props();
</script>

<div class="w-full h-16"></div>
<header class="bg-background fixed left-0 right-0 top-0 z-50 h-16 w-full">
	<div
		class="center-content shadow-inner-sym-[10px] bg-inset dark:shadow-inner-sym-10 grid h-full
	grid-cols-3 items-center overflow-hidden shadow-black mt-1.5"
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

		</div>
	</div>
</header>
{#if loadingBar.visible}
	<div
		class="top-18 z-60 bg-primary fixed left-0 right-0 h-[3px] origin-left rounded-full"
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
