<script lang="ts" generics="TFilterState extends FilterState">
	import { documentStore, type FilterState } from '$lib/runes/document.svelte';
	import EyeOpen from '~icons/mdi/eye';
	import EyeClosed from '~icons/mdi/eye-off';
	import ChevronUp from '~icons/material-symbols/keyboard-arrow-up';
	import type { Snippet } from 'svelte';
	import ClearFilterIcon from '~icons/mdi/filter-remove-outline';

	type FilterData = TFilterState extends FilterState<infer U> ? U : never;

	interface Props {
		header: string | Snippet<[boolean]>;
		placeholderLabel?: string;
		compact?: boolean;
		filters: TFilterState[];
		item: Snippet<[FilterState<FilterData>, boolean]>;
	}

	let {
		placeholderLabel,
		header = 'Filter',
		compact = false,
		filters = [],
		item
	}: Props = $props();
	let isExpanded = $state(true);

	const handleClick = (filter: FilterState) => {
		documentStore.filters.toggle(filter);
		hoveredId = null;
		justClickedId = filter.id; // Mark as just clicked to ignore spurious mouseenter from re-render
	};
	let hoveredId = $state<number | null>(null);
	let justClickedId = $state<number | null>(null);
</script>

{#snippet filterStateElement(hovered: boolean, filterState: FilterState<FilterData>)}
	{#if filterState?.value === 'include'}
		{#if hovered}
			<div title="Hide highlights by this user" class="opacity-70">
				<EyeClosed />
			</div>
		{:else}
			<div>
				<EyeOpen />
			</div>
		{/if}
	{:else if filterState?.value === 'exclude'}
		{#if hovered}
			<div title="Clear Filter" class="opacity-70">
				<ClearFilterIcon />
			</div>
		{:else}
			<div>
				<EyeClosed />
			</div>
		{/if}
	{:else if hovered}
		<div title="Include highlights by this user" class="opacity-70">
			<EyeOpen />
		</div>
	{/if}
{/snippet}

{#if filters.length > 0}
	<div
		class="{isExpanded ? 'mb-6' : ''} flex flex-col {compact &&
			'items-center'} h-fit w-full gap-2 overflow-x-hidden overflow-y-auto"
	>
		<!--Header if expanded-->
		{#if !(typeof header === 'string' && compact)}
			<button
				class="mb-1 flex cursor-pointer items-center justify-between text-[10px] text-text/70 transition-colors hover:text-text"
				onclick={() => (isExpanded = !isExpanded)}
			>
				{#if !compact}
					{#if typeof header === 'string'}
						<span>{header}</span>
					{:else}
						{@render header(compact)}
					{/if}
					{#if !compact}
						<span
							class="inline-flex transition-transform duration-200 ease-in-out {isExpanded
								? ''
								: 'rotate-180'}"
						>
							<ChevronUp />
						</span>
					{/if}
				{:else if typeof header !== 'string'}
					{@render header(compact)}
				{/if}
			</button>
		{/if}

		{#if isExpanded}
			<!--Scrollable List of active filters-->
			<div
				class="flex h-full w-full flex-col {!compact ? 'justify-between' : 'items-center'} gap-1.5"
			>
				{#each filters as filter (filter)}
					{@const hovered = hoveredId === filter.id}
					<button
						class="flex w-full cursor-pointer items-center justify-between gap-2 rounded text-text/70 transition-colors hover:text-text"
						onclick={() => handleClick(filter)}
						onmouseenter={() => {
							// Ignore mouseenter if this filter was just clicked (prevents spurious hover from re-render)
							if (justClickedId !== filter.id) {
								hoveredId = filter.id;
							}
						}}
						onmouseleave={() => {
							hoveredId = null;
							justClickedId = null; // Clear just-clicked flag on leave so next enter works normally
						}}
					>
						<div
							class="relative flex max-w-full grow flex-row items-center gap-2 {!compact
								? 'justify-between'
								: 'justify-center'}"
						>
							{@render item(filter as unknown as FilterState<FilterData>, compact)}
							{#if compact}
								<div
									class="absolute -top-0.5 right-2 flex h-1.5 w-1.5 items-center justify-center rounded-full p-0.5"
								>
									{@render filterStateElement(
										hovered,
										filter as unknown as FilterState<FilterData>
									)}
								</div>
							{:else}
								{@render filterStateElement(hovered, filter as unknown as FilterState<FilterData>)}
							{/if}
						</div>
					</button>
				{/each}
			</div>
		{/if}
	</div>
{:else if !compact && placeholderLabel}
	<span class="px-1 text-[10px] text-text/60">{placeholderLabel}</span>
{/if}
