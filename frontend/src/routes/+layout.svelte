<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import Footer from '$lib/components/footer.svelte';
	import Header from '$lib/components/header.svelte';
	import Notification from '$lib/components/notifications.svelte';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<div class="flex flex-col items-center w-full min-h-screen mt-2 bg-background text-text transition-all">
	<Header />
	<Notification />
	<div
		class="flex flex-col w-full mt-[4.15rem] grow overflow-auto items-center"
		style="scrollbar-gutter: stable both-edges;"
	>
		<main class="grow w-full max-w-260 flex flex-col">
			{@render children?.()}
		</main>
		<div class="shadow-inner shadow-black min-h-2 mt-4 rounded w-[98%] mx-auto"></div>
		<Footer />
	</div>
</div>
