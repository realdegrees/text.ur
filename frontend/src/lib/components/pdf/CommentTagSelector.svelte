<script lang="ts">
	import AddIcon from '~icons/material-symbols/add-2-rounded';
	import type { TagRead } from '$api/types';
	import Badge from '$lib/components/badge.svelte';
	import Dropdown from '$lib/components/dropdown.svelte';

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

	// Drag and drop state
	let draggedTagId = $state<number | null>(null);
	let dragOverTagId = $state<number | null>(null);

	function handleDragStart(tagId: number) {
		draggedTagId = tagId;
	}

	function handleDragOver(e: DragEvent, tagId: number) {
		e.preventDefault();
		if (draggedTagId !== tagId) {
			dragOverTagId = tagId;
		}
	}

	function handleDragLeave() {
		dragOverTagId = null;
	}

	function handleDrop(e: DragEvent, targetTagId: number) {
		e.preventDefault();
		if (draggedTagId === null || draggedTagId === targetTagId) {
			draggedTagId = null;
			dragOverTagId = null;
			return;
		}

		const draggedIndex = selectedTags.findIndex((t) => t.id === draggedTagId);
		const targetIndex = selectedTags.findIndex((t) => t.id === targetTagId);

		if (draggedIndex === -1 || targetIndex === -1) {
			draggedTagId = null;
			dragOverTagId = null;
			return;
		}

		// Reorder the tags
		const tagsCopy = [...selectedTags];
		const [draggedTag] = tagsCopy.splice(draggedIndex, 1);
		tagsCopy.splice(targetIndex, 0, draggedTag);
		selectedTags = tagsCopy;

		draggedTagId = null;
		dragOverTagId = null;
	}

	function handleDragEnd() {
		draggedTagId = null;
		dragOverTagId = null;
	}
</script>

<div class="flex w-full flex-wrap items-center gap-1.5">
	{#each selectedTags as tag (tag.id)}
		<div
			role="button"
			tabindex="0"
			draggable="true"
			ondragstart={() => handleDragStart(tag.id)}
			ondragover={(e) => handleDragOver(e, tag.id)}
			ondragleave={handleDragLeave}
			ondrop={(e) => handleDrop(e, tag.id)}
			ondragend={handleDragEnd}
			class="cursor-move transition-opacity {draggedTagId === tag.id
				? 'opacity-50'
				: ''} {dragOverTagId === tag.id ? 'rounded ring-2 ring-primary' : ''}"
		>
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
			title="Add Tag"
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
