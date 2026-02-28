<script lang="ts">
	import AddIcon from '~icons/material-symbols/add-2-rounded';
	import DragIcon from '~icons/material-symbols/drag-indicator';
	import type { TagRead } from '$api/types';
	import Badge from '$lib/components/badge.svelte';
	import Dropdown from '$lib/components/dropdown.svelte';
	import LL from '$i18n/i18n-svelte';
	import { sortable } from '$lib/actions/sortable';

	interface Props {
		selectedTags: TagRead[];
		availableTags: TagRead[];
		onAdd?: (tag: TagRead) => void;
		onRemove?: (tag: TagRead) => void;
		disabled?: boolean;
		showRemove?: boolean;
		allowSelection?: boolean;
	}

	let {
		selectedTags = $bindable([]),
		availableTags = [],
		onAdd,
		onRemove,
		disabled = false,
		showRemove = true,
		allowSelection = true
	}: Props = $props();

	const availableToAdd = $derived(
		availableTags.filter((tag) => !selectedTags.some((selected) => selected.id === tag.id))
	);

	function handleReorder(fromIndex: number, toIndex: number) {
		const tagsCopy = [...selectedTags];
		const [moved] = tagsCopy.splice(fromIndex, 1);
		tagsCopy.splice(toIndex, 0, moved);
		selectedTags = tagsCopy;
	}
</script>

<div
	class="flex w-full flex-wrap items-center gap-1.5"
	use:sortable={{ onReorder: handleReorder, enabled: !disabled }}
>
	{#each selectedTags as tag (tag.id)}
		<div data-sortable-id={tag.id} class="flex items-center gap-0.5">
			<span data-drag-handle class="flex cursor-grab items-center text-text/40 hover:text-text/70">
				<DragIcon class="h-3.5 w-3.5" />
			</span>
			<Badge
				item={tag}
				label={tag.label}
				{showRemove}
				onRemove={() => onRemove?.(tag)}
				{disabled}
				customColor={tag.color}
			/>
		</div>
	{/each}

	{#if availableToAdd.length > 0}
		<Dropdown
			items={availableToAdd}
			onSelect={(tag) => onAdd?.(tag)}
			position="bottom-left"
			title={$LL.tags.addTag()}
			showArrow={false}
			show={false}
			hideCurrentSelection={true}
			{allowSelection}
		>
			{#snippet icon()}
				<div
					class={`flex items-center gap-1 rounded bg-background px-2 py-1 text-sm text-text shadow-inner shadow-black/20 transition-all hover:bg-green-500/30 ${disabled ? 'cursor-not-allowed opacity-50' : ''}`}
				>
					<AddIcon class="h-4 w-4" />
					<span>Add tag</span>
				</div>
			{/snippet}
			{#snippet itemSnippet(tag)}
				<div class="flex items-center gap-2 p-1 text-left text-text">
					<div
						class="h-3 w-3 rounded-full"
						style="background-color: {tag.color}"
						title={tag.label}
					></div>
					<p>{tag.label}</p>
				</div>
			{/snippet}
		</Dropdown>
	{/if}
</div>
