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

	let { children, data } = $props();

	// Check for email verification
	$effect(() => {
		const verified = page.url.searchParams.get('verified') === 'true';
		if (verified) {
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
	class="flex min-h-screen w-full flex-col items-center bg-background text-text transition-all"
>
	<Header user={data.sessionUser} />
	<Notification />
	<div
		class="grow flex-col items-center w-full"
	>
		<main class="flex w-full grow flex-col">
			{@render children?.()}
		</main>
		<div class="mx-auto mt-4 min-h-2 w-[99%] rounded shadow-inner shadow-black"></div>
		<Footer />
	</div>
</div>
