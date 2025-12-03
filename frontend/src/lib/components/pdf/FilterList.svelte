<script lang="ts" generics="TFilterState extends FilterState">
	import { documentStore, type FilterState } from '$lib/runes/document.svelte';
	import RemoveIcon from '~icons/material-symbols/remove';
	import EyeOpen from '~icons/mdi/eye';
	import EyeClosed from '~icons/mdi/eye-off';
	import ChevronUp from '~icons/material-symbols/keyboard-arrow-up';
	import type { Snippet } from 'svelte';

	type FilterData = TFilterState extends FilterState<infer U> ? U : never;

	interface Props {
		label: string;
		placeholderLabel?: string;
		compact?: boolean;
		filters: TFilterState[];
		item: Snippet<[FilterState<FilterData>, boolean]>;
	}

	let { placeholderLabel, label = 'Filter', compact = false, filters = [], item }: Props = $props();
	let isExpanded = $state(true);

	const handleClick = (filter: FilterState) => {
		documentStore.filters.toggle(filter);
		hoveredId = null; // Reset hover state on click to not show the hover icon immediately which would be confusing
	};
	let hoveredId = $state<number | null>(null);
</script>

{#snippet filterStateElement(hovered: boolean, filterState: FilterState<FilterData>)}
	{#if filterState?.value === 'include'}
		{#if hovered}
			<div title="Hide highlights by this user" class="opacity-40">
				<EyeClosed />
			</div>
		{:else}
			<div>
				<EyeOpen />
			</div>
		{/if}
	{:else if filterState?.value === 'exclude'}
		{#if hovered}
			<div title="Clear Filter" class="opacity-40">
				<RemoveIcon />
			</div>
		{:else}
			<div>
				<EyeClosed />
			</div>
		{/if}
	{:else if hovered}
		<div title="Include highlights by this user" class="opacity-40">
			<EyeOpen />
		</div>
	{/if}
{/snippet}

{#if filters.length > 0}
	<div
		class="flex flex-col mb-4 {compact &&
			'items-center'} h-fit w-full gap-2 overflow-y-auto overflow-x-hidden"
	>
		<!--Header if expanded-->
		{#if !compact}
			<button
				class="text-text/40 hover:text-text/60 flex cursor-pointer items-center justify-between px-1 text-[10px] transition-colors"
				onclick={() => (isExpanded = !isExpanded)}
			>
				<span>{label}</span>
				<span class="inline-flex transition-transform duration-200 ease-in-out {isExpanded ? '' : 'rotate-180'}">
					<ChevronUp />
				</span>
			</button>
		{/if}

		{#if isExpanded}
			<!--Scrollable List of active users-->
			<div
				class="flex h-full w-full flex-col {!compact
					? 'justify-between'
					: 'items-center'} gap-3 overflow-y-auto"
			>
					{#each filters as filter (label + filter.id)}
						{@const hovered = hoveredId === filter.id}
						<button
							class="text-text/70 flex cursor-pointer items-center justify-between gap-2 rounded"
							onclick={() => handleClick(filter)}
							onmouseenter={() => (hoveredId = filter.id)}
							onmouseleave={() => (hoveredId = null)}
						>
							<div class="flex flex-row items-center gap-2">
								<div class="relative">
									{@render item(filter as unknown as FilterState<FilterData>, compact)}
									{#if compact}
										<div
											class="absolute -top-1 left-0.5 flex h-3 w-3 items-center justify-center rounded-full p-0.5"
										>
											{@render filterStateElement(
												hovered,
												filter as unknown as FilterState<FilterData>
											)}
										</div>
									{/if}
								</div>
							</div>
							{#if !compact}
								{@render filterStateElement(hovered, filter as unknown as FilterState<FilterData>)}
							{/if}
						</button>
					{/each}
			</div>
		{/if}
	</div>
{:else if !compact && placeholderLabel}
	<span class="text-text/40 px-1 text-[10px]">{placeholderLabel}</span>
{/if}
