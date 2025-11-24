<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import Footer from '$lib/components/footer.svelte';
	import Header from '$lib/components/header.svelte';
	import Notification from '$lib/components/notifications.svelte';
	import { LL } from '$i18n/i18n-svelte';
	import { notification } from '$lib/stores/notificationStore';
	import { page } from '$app/state';
	import { loadingBar } from '$lib/stores/loadingBar.svelte';
	import { browser } from '$app/environment';
	import { sessionStore } from '$lib/runes/session.svelte';

	let { children, data } = $props();

	// Track the search string reactively to ensure the effect triggers on URL changes
	const verifiedParam = $derived(page.url.searchParams.get('verified'));

	// Check for email verification
	$effect(() => {
		if (!browser) return;

		// Initialize session store with user and membership data
		sessionStore.currentUser = data.sessionUser;
		sessionStore.routeMembership = data.routeMembership;

		if (verifiedParam === 'true') {
			notification('success', $LL.emailVerified(), { duration: 10 * 1000 });
			loadingBar.one_shot();
			// Remove the verified param from the URL
			const url = new URL(page.url);
			url.searchParams.delete('verified');
			history.replaceState(null, '', url.toString());
		}
	});
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<div
	class="flex h-screen custom-scrollbar w-full flex-col items-center overflow-hidden bg-background text-text transition-all"
>
	<Header user={data.sessionUser} />
	<Notification />
	<div class="min-h-0 w-full flex-1 flex-col items-center">
		<main class="flex h-full w-full flex-1">
			{@render children?.()}
		</main>
	</div>
	<Footer />
</div>
