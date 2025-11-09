<script lang="ts" generics="Item extends unknown">
	import type { Paginated } from '$api/pagination';
	import type { Filter } from '$api/types';
	import { filterToSearchParams } from '$lib/util/filters';
	import type { Snippet } from 'svelte';
	import { onMount } from 'svelte';
	import ChevronDown from '~icons/material-symbols/keyboard-arrow-down';

	let {
		itemSnippet,
		data,
		url,
		step = 20,
		filters = [],
		autoLoad = true,
		onSelect
	}: {
		itemSnippet: Snippet<[Item]>;
		data: Paginated<Item>;
		url: string;
		step?: number;
		filters?: Filter[];
		autoLoad?: boolean;
		onSelect?: (item: Item) => void;
	} = $props();

	let items = $derived(data.data);
	let hasMore = $derived(data.data.length < data.total);

	$effect.pre(() => {
		// reset when filters change
		// eslint-disable-next-line @typescript-eslint/no-unused-vars
		const f = filters;
		handleLoadMore(true);
	});

	let loadingMore = $state(false);
	let sentinel = $state<HTMLDivElement>();
	let observer: IntersectionObserver | null = null;

	async function handleLoadMore(reset = false) {
		if (loadingMore || (!reset && !hasMore)) return;

		loadingMore = true;

		if (reset) {
			data = {
				data: [],
				limit: step,
				offset: 0,
				total: data.total
			};
		}
		try {
			const searchParams = filterToSearchParams(...filters);
			searchParams.append('offset', String(Math.min(data.offset + data.limit, data.total)));
			searchParams.append('limit', String(Math.min(step, data.total - data.offset)));
			const res = await fetch(`${url}?${searchParams}`);
			const block = (await res.json()) as Paginated<Item>;
			data = {
				data: [...data.data, ...block.data],
				limit: block.limit,
				offset: block.offset,
				total: block.total
			};
		} finally {
			loadingMore = false;
		}
	}

	function createObserver() {
		if (!autoLoad) return;
		if (observer) observer.disconnect();
		observer = new IntersectionObserver(
			(entries) => {
				for (const e of entries) {
					if (e.isIntersecting) handleLoadMore();
				}
			},
			{ root: null, rootMargin: '200px', threshold: 0.1 }
		);
		if (sentinel) observer.observe(sentinel);
	}

	onMount(() => {
		createObserver();
		if (items.length === 0) handleLoadMore();
		return () => {
			if (observer) observer.disconnect();
		};
	});
</script>

<!-- Scrollable Container -->
<div class="h-full custom-scrollbar flex-1 overflow-y-auto">
	<ul class="w-full">
		{#each items as item (item)}
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
	<div bind:this={sentinel} class="h-4 w-full"></div>

	{#if hasMore && !loadingMore && !autoLoad}
		<button
			class="flex w-full cursor-pointer items-center justify-center rounded bg-inset py-1 shadow-inner-sym-[5px] shadow-black transition-shadow hover:shadow-inner-sym-[10px]"
			onclick={() => handleLoadMore()}
			aria-label="Load more items"
		>
			<ChevronDown class="h-8 w-8 " />
		</button>
	{/if}
</div>
