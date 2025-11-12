<script lang="ts" generics="Item extends Record<string, any>">
	import type { Paginated } from '$api/pagination';
	import type { Snippet } from 'svelte';
	import ChevronDown from '~icons/material-symbols/keyboard-arrow-down';
	import { infiniteScroll } from '$lib/util/infiniteScroll.svelte';

	let {
		itemSnippet,
		data: initialData,
		loadMore,
		step = 20,
		autoLoad = true,
		onSelect
	}: {
		itemSnippet: Snippet<[Item]>;
		data: Paginated<Item>;
		loadMore: (offset: number, limit: number) => Promise<Paginated<Item>>;
		step?: number;
		autoLoad?: boolean;
		onSelect?: (item: Item) => void;
	} = $props();

	const scroll = infiniteScroll(initialData, loadMore, step, autoLoad);
</script>

<!-- Scrollable Container -->
<div class="h-full custom-scrollbar flex-1 overflow-y-auto">
	<ul class="w-full">
		{#each scroll.items as item (item)}
			<li class="mr-1">
				{#if onSelect}
					<button
						class="block w-full cursor-pointer rounded-sm hover:bg-primary"
						onclick={() => onSelect(item)}
					>
						{@render itemSnippet(item as Item)}
					</button>
				{:else}
					<div class="block w-full rounded-sm hover:bg-primary">
						{@render itemSnippet(item as Item)}
					</div>
				{/if}
			</li>
		{/each}
	</ul>

	<!-- Infinite Scroll Sentinel -->
	<div bind:this={scroll.sentinel.node} class="h-4 w-full"></div>

	{#if scroll.hasMore && !scroll.loadingMore && !autoLoad}
		<button
			class="flex w-full cursor-pointer items-center justify-center rounded bg-inset py-1 shadow-inner-sym-[5px] shadow-black transition-shadow hover:shadow-inner-sym-[10px]"
			onclick={() => scroll.handleLoadMore()}
			aria-label="Load more items"
		>
			<ChevronDown class="h-8 w-8 " />
		</button>
	{/if}
</div>
