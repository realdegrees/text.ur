<script lang="ts">
	import { browser } from '$app/environment';
	import { goto, invalidateAll } from '$app/navigation';
	import AppLogoDark from '$lib/images/logo/logo_dark.svg';
	import AppLogoLight from '$lib/images/logo/logo_light.svg';
	import darkMode from '$lib/stores/darkMode.svelte';
	import { loadingBar } from '$lib/stores/loadingBar.svelte';
	import { api } from '$api/client';
	import { notification } from '$lib/stores/notificationStore';
	import LoginIcon from '~icons/material-symbols/login';
	import type { UserPrivate } from '$api/types';
	import ProfileImageFallback from '~icons/material-symbols/account-box';
	import Dropdown from '$lib/components/dropdown.svelte';
	import AccountIcon from '~icons/mdi/account-cog';
	import LogoutIcon from '~icons/mdi/exit-run';
	import { page } from '$app/state';
	import LL from '$i18n/i18n-svelte';

	let { user }: { user?: UserPrivate } = $props();

	// Use dark logo as default during SSR to avoid hydration mismatch,
	// then reactively update on client based on actual theme preference
	let logoSrc = $derived(browser ? (darkMode.enabled ? AppLogoLight : AppLogoDark) : AppLogoDark);

	// Dropdown state
	let showUserMenu = $state(false);

	type UserMenuItem = 'account' | 'logout';
	const menuItems: UserMenuItem[] = ['account', 'logout'];

	async function handleMenuItemSelect(item: UserMenuItem) {
		if (item === 'account') {
			await goto(`/users/${user?.id}/account`);
		} else if (item === 'logout') {
			await handleLogout();
		}
		// logout is handled by ConfirmButton in the itemSnippet
	}

	async function handleLogout() {
		const result = await api.post('/logout', {});

		if (!result.success) {
			notification(result.error);
			return;
		}

		// Close the dropdown
		showUserMenu = false;

		// Redirect to login page after logout
		invalidateAll();
		await goto('/login');
	}
</script>

<div class="h-16.5 w-full"></div>
<header class="fixed top-0 right-0 left-0 z-9000 h-15.5 w-full bg-background">
	<div
		class="center-content dark:shadow-inner-sym-10 mt-1 grid h-full grid-cols-3
	items-center bg-inset shadow-inner-sym-[10px] shadow-black"
	>
		<a
			href="/"
			class="col-span-1 col-start-1 flex flex-row justify-self-start transition-all hover:pl-0.5"
		>
			<img class="w-auto p-2" src={logoSrc} alt="Logo" />
			<p class="ml-1 self-center text-3xl"></p>
		</a>

		<div class="col-span-1 col-start-3 mr-3 flex flex-row-reverse items-center justify-self-end">
			{#if user?.id}
				<div class="relative z-9500">
					<button
						class="flex w-full flex-row items-center rounded-lg px-2 py-1 transition-colors hover:bg-text/5"
						onclick={(e) => {
							e.stopPropagation();
							showUserMenu = !showUserMenu;
						}}
					>
						<ProfileImageFallback class="h-9 w-9" />
						<!--TODO insert user profile image if that feature is added-->
						<p class="ml-1 font-semibold">
							{user.first_name && user.last_name
								? `${user.first_name} ${user.last_name}`
								: user.username}
						</p>
					</button>

					<Dropdown
						items={menuItems}
						bind:show={showUserMenu}
						position="bottom-right"
						allowSelection={false}
						showCurrentItemInList={true}
						onSelect={handleMenuItemSelect}
					>
						{#snippet itemSnippet(item)}
							{#if item === 'account'}
								<div class="flex w-full items-center gap-2 px-3 py-2 text-sm">
									<AccountIcon class="h-5 w-5" />
									<p>Account Settings</p>
								</div>
							{:else if item === 'logout' && !user.is_guest}
								<div
									class="flex w-full items-center gap-2 px-3 py-2 text-sm text-red-600 transition-colors dark:text-red-400"
								>
									<LogoutIcon class="h-5 w-5" />
									<p>Logout</p>
								</div>
							{/if}
						{/snippet}
					</Dropdown>
				</div>
			{:else if page.url.pathname !== '/login'}
				<button
					class="bg-discord group flex h-full w-full clickable flex-row items-center justify-between rounded p-1"
					onclick={() => goto('/login')}
				>
					<LoginIcon />
					<p class="ml-1 font-semibold">{$LL.login()}</p>
				</button>
			{/if}
		</div>
	</div>
</header>
{#if loadingBar.visible}
	<div
		class="fixed top-0 right-0 left-0 z-60 h-1 rounded-full bg-primary transition-transform duration-500 ease-out"
		class:origin-right={loadingBar.shrinking}
		class:origin-left={!loadingBar.shrinking}
		class:scale-x-0={loadingBar.shrinking}
		class:scale-x-100={!loadingBar.shrinking}
		style="width: {loadingBar.progress}%"
	></div>
{/if}

<style lang="postcss">
	@reference '../app.css';

	header * {
		@apply max-h-16;
	}
	a {
		@apply text-center;
	}
</style>
