<script lang="ts" generics="Item, ExcludedFields extends PropertyKey = never">
	import type { Paginated } from '$api/pagination';
	import type { Snippet } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import ChevronDown from '~icons/material-symbols/keyboard-arrow-down';
	import { infiniteScroll } from '$lib/util/infiniteScroll.svelte';

	type ColumnConfig<T> = {
		label: string;
		width?: string;
		snippet: Snippet<[T]>;
	};

	type ActualItem = Omit<Item, ExcludedFields & keyof Item>;

	let {
		data: initialData,
		columns,
		loadMore,
		step = 20,
		autoLoad = true,
		selectable = false,
		onSelectionChange,
		headerBgClass = '',
		rowBgClass = ''
	}: {
		columns: ColumnConfig<ActualItem>[];
		data: Paginated<Item, ExcludedFields>;
		loadMore: (
			offset: number,
			limit: number
		) => Promise<Paginated<Item, ExcludedFields> | undefined>;
		step?: number;
		autoLoad?: boolean;
		selectable?: boolean;
		onSelectionChange?: (selectedItems: ActualItem[]) => void;
		headerBgClass?: string;
		rowBgClass?: string;
	} = $props();

	const scroll = infiniteScroll(initialData, loadMore, step, autoLoad);

	// Convert simple string array to column configs
	const columnConfigs = $derived.by(() => {
		return columns.map((col) => {
			return {
				...col,
				label: col.label,
				width: col.width || 'auto'
			} as ColumnConfig<ActualItem>;
		});
	});

	let selectedItems = $state.raw(new SvelteSet<ActualItem>());
	let allSelected = $derived(
		selectable && scroll.items.length > 0 && scroll.items.every((item) => selectedItems.has(item))
	);

	$effect(() => {
		if (onSelectionChange) {
			onSelectionChange(Array.from(selectedItems));
		}
	});

	function toggleSelectAll() {
		const currentlyAllSelected =
			scroll.items.length > 0 && scroll.items.every((item) => selectedItems.has(item));
		if (currentlyAllSelected) {
			selectedItems.clear();
		} else {
			scroll.items.forEach((item) => selectedItems.add(item));
		}
	}

	function toggleSelection(item: ActualItem) {
		if (selectedItems.has(item)) {
			selectedItems.delete(item);
		} else {
			selectedItems.add(item);
		}
		selectedItems = selectedItems; // trigger reactivity
	}
</script>

<div class="flex h-full flex-col overflow-hidden">
	<!-- Fixed Table Header -->
	<div class="sticky top-0 z-10 shadow-sm {headerBgClass}">
		<div
			class="grid items-center gap-3 border-b border-gray-300 px-4 py-2 text-xs font-semibold tracking-wide text-gray-600 uppercase"
			style="grid-template-columns: {selectable ? '30px ' : ''}{columnConfigs
				.map((c) => c.width)
				.join(' ')};"
		>
			{#if selectable}
				<div class="flex items-center justify-center min-w-0">
					<input
						type="checkbox"
						checked={allSelected}
						onchange={toggleSelectAll}
						class="h-4 w-4 cursor-pointer"
						aria-label="Select all"
					/>
				</div>
			{/if}
			{#each columnConfigs as col (col)}
				<div class="min-w-0">{col.label}</div>
			{/each}
		</div>
	</div>

	<!-- Scrollable Table Body -->
	<div bind:this={scroll.scrollContainer.node} class="custom-scrollbar flex-1 overflow-y-auto">
		<div>
			{#each scroll.items as item, index (item)}
				<div
					class="grid items-center gap-3 px-4 py-2 transition-colors {index % 2 === 0
						? rowBgClass
						: 'color-mix(rowBgClass, bg-inset)'}"
					style="grid-template-columns: {selectable ? '30px ' : ''}{columnConfigs
						.map((c) => c.width)
						.join(' ')};"
				>
					{#if selectable}
						<div class="flex items-center justify-center min-w-0">
							<input
								type="checkbox"
								checked={selectedItems.has(item)}
								onchange={() => toggleSelection(item)}
								class="h-4 w-4 cursor-pointer"
								aria-label="Select row"
							/>
						</div>
					{/if}
					{#each columnConfigs as col (col)}
						<div class="text-sm text-gray-700 min-w-0">
							{#if col.snippet}
								{@render col.snippet(item)}
							{:else}
								Missing snippet
							{/if}
						</div>
					{/each}
				</div>
			{/each}
		</div>

		<!-- Infinite Scroll Sentinel -->
		<div bind:this={scroll.sentinel.node} class="h-4 w-full"></div>

		{#if scroll.hasMore && !scroll.loadingMore && !autoLoad}
			<button
				class="flex w-full cursor-pointer items-center justify-center rounded py-1 shadow-sm transition-shadow hover:shadow-md"
				onclick={() => scroll.handleLoadMore()}
				aria-label="Load more items"
			>
				<ChevronDown class="h-8 w-8" />
			</button>
		{/if}

		{#if scroll.loadingMore}
			<div class="flex w-full items-center justify-center py-4">
				<div class="text-sm text-gray-500">Loading...</div>
			</div>
		{/if}
	</div>
</div>
