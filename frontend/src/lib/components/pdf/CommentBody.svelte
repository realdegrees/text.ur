<script lang="ts">
	/*
  Simple presentational component to render the body of a single comment.
  Extracted to avoid duplicated UI between CommentCard.svelte and CommentGroup.svelte.
  */
	import type { CommentRead } from '$api/types';
	import type { Annotation } from '$types/pdf';
	import DeleteIcon from '~icons/material-symbols/delete-outline';

	interface Props {
		comment: CommentRead;
		annotation: Annotation;
		showDeleteConfirm: boolean;
		onDeleteClick?: (event: MouseEvent) => void;
		onDeleteConfirm?: (event: MouseEvent) => void;
		onDeleteCancel?: (event: MouseEvent) => void;
	}

	let {
		comment,
		annotation,
		showDeleteConfirm = false,
		onDeleteClick = () => {},
		onDeleteConfirm = () => {},
		onDeleteCancel = () => {}
	}: Props = $props();
</script>

{#if showDeleteConfirm}
	<div
		class="flex flex-col gap-2"
		onclick={(e) => e.stopPropagation()}
		onkeydown={(e) => {
			if (e.key === 'Escape') {
				onDeleteCancel(e as any);
			}
		}}
		role="dialog"
		aria-label="Delete confirmation"
		tabindex="-1"
	>
		<p class="text-sm font-semibold text-red-600">Delete this highlight?</p>
		<div class="flex gap-2">
			<button
				onclick={onDeleteConfirm}
				class="rounded-md bg-red-500 px-3 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-red-600"
			>
				Delete
			</button>
			<button
				onclick={onDeleteCancel}
				class="rounded-md bg-gray-200 px-3 py-1.5 text-xs font-semibold text-gray-700 transition-colors hover:bg-gray-300"
			>
				Cancel
			</button>
		</div>
	</div>
{:else}
	<div>
		<div class="mb-2 flex items-center justify-between">
			<div class="flex items-center gap-2">
				<div class="h-3 w-3 rounded-full" style:background-color={annotation.color}></div>
				<span class="text-xs font-semibold text-gray-700">
					{comment.user?.username ?? 'Anonymous'}
				</span>
			</div>
			<button
				onclick={onDeleteClick}
				class="text-gray-400 transition-colors hover:text-red-600"
				aria-label="Delete comment"
			>
				<DeleteIcon class="h-4 w-4" />
			</button>
		</div>
		{#if annotation.text}
			<p class="mb-2 text-xs text-gray-500 italic">
				"{annotation.text.substring(0, 100)}{annotation.text.length > 100 ? '...' : ''}"
			</p>
		{/if}
		{#if comment.content}
			<p class="text-sm leading-relaxed text-gray-800">{comment.content}</p>
		{:else}
			<p class="text-xs text-gray-400 italic">No comment added</p>
		{/if}
	</div>
{/if}
