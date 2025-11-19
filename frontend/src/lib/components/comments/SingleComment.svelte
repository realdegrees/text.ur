<script lang="ts">
	import type { CommentRead } from '$api/types.js';
	import type { Annotation } from '$types/pdf';
	import DeleteIcon from '~icons/material-symbols/delete-outline';

	let {
		comment,
		annotation,
		expanded,
		showDeleteConfirm,
		actualTop,
		onCommentClick,
		onMouseEnter,
		onMouseLeave,
		onDeleteClick,
		onDeleteConfirm,
		onDeleteCancel
	}: {
		comment: CommentRead;
		annotation: Annotation;
		expanded: boolean;
		showDeleteConfirm: boolean;
		actualTop: number;
		onCommentClick: (event: MouseEvent) => void;
		onMouseEnter: () => void;
		onMouseLeave: () => void;
		onDeleteClick: (event: MouseEvent) => void;
		onDeleteConfirm: (event: MouseEvent) => void;
		onDeleteCancel: (event: MouseEvent) => void;
	} = $props();
</script>

{#if expanded}
	<!-- Expanded comment card -->
	<div
		data-comment-id={comment.id}
		class="absolute left-0 right-4 rounded border-l-4 bg-white px-3 py-2 shadow-md transition-all duration-200"
		style:top="{actualTop}px"
		style:border-left-color={annotation.color}
		onmouseenter={onMouseEnter}
		onmouseleave={onMouseLeave}
		onclick={onCommentClick}
		onkeydown={(e) => {
			if (e.key === 'Enter' || e.key === ' ') {
				e.preventDefault();
				onCommentClick(e as any);
			}
		}}
		role="button"
		tabindex="0"
	>
		{#if showDeleteConfirm}
			<!-- Delete confirmation -->
			<!-- svelte-ignore a11y_click_events_have_key_events -->
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<div class="flex flex-col gap-2" onclick={(e) => e.stopPropagation()}>
				<p class="text-xs font-semibold text-red-600">Delete this comment?</p>
				<div class="flex gap-2">
					<button
						onclick={onDeleteConfirm}
						class="rounded bg-red-500/20 px-2 py-1 text-xs font-semibold text-red-600 hover:bg-red-500/30"
					>
						Delete
					</button>
					<button
						onclick={onDeleteCancel}
						class="rounded bg-gray-200 px-2 py-1 text-xs font-semibold text-gray-700 hover:bg-gray-300"
					>
						Cancel
					</button>
				</div>
			</div>
		{:else}
			<!-- Normal comment display -->
			<div class="mb-1 flex items-center justify-between">
				<span class="text-xs font-medium text-gray-600">
					{comment.user?.username ?? 'Anonymous'}
				</span>
				<button
					onclick={onDeleteClick}
					class="text-gray-400 hover:text-red-600"
					aria-label="Delete comment"
				>
					<DeleteIcon class="h-4 w-4" />
				</button>
			</div>
			{#if comment.content}
				<p class="text-sm text-gray-800 leading-snug">{comment.content}</p>
			{:else}
				<p class="text-xs italic text-gray-400">No comment added</p>
			{/if}
		{/if}
	</div>
{:else}
	<!-- Collapsed badge indicator -->
	<div
		data-comment-id={comment.id}
		class="absolute right-4 rounded-full px-2 py-1 shadow-sm transition-all duration-200 cursor-pointer hover:shadow-md"
		style:top="{actualTop}px"
		style:background-color={annotation.color}
		onmouseenter={onMouseEnter}
		onmouseleave={onMouseLeave}
		onclick={onCommentClick}
		onkeydown={(e) => {
			if (e.key === 'Enter' || e.key === ' ') {
				e.preventDefault();
				onCommentClick(e as any);
			}
		}}
		role="button"
		tabindex="0"
	>
		<span class="text-xs font-medium text-gray-800">
			{comment.user?.username ?? 'Anonymous'}
		</span>
	</div>
{/if}
