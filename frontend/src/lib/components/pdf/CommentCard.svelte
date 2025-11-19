<script lang="ts">
	import type { CommentRead } from '$api/types';
	import type { Annotation } from '$types/pdf';
	import DeleteIcon from '~icons/material-symbols/delete-outline';
	import { fly, scale } from 'svelte/transition';
	import { quintOut } from 'svelte/easing';

	interface Props {
		comment: CommentRead;
		annotation: Annotation;
		expanded: boolean;
		showDeleteConfirm: boolean;
		top: number;
		hoverDelayMs?: number;
		onClick?: (event: MouseEvent) => void;
		onMouseEnter?: () => void;
		onMouseLeave?: () => void;
		onDeleteClick?: (event: MouseEvent) => void;
		onDeleteConfirm?: (event: MouseEvent) => void;
		onDeleteCancel?: (event: MouseEvent) => void;
	}

	let {
		comment,
		annotation,
		expanded,
		showDeleteConfirm,
		top,
		hoverDelayMs = 200,
		onClick = () => {},
		onMouseEnter = () => {},
		onMouseLeave = () => {},
		onDeleteClick = () => {},
		onDeleteConfirm = () => {},
		onDeleteCancel = () => {}
	}: Props = $props();

	let lastHoverTime = $state(0);
	let leaveTimer: ReturnType<typeof setTimeout> | null = $state(null);

	function handleMouseEnter() {
		// Clear any pending leave timer
		if (leaveTimer) {
			clearTimeout(leaveTimer);
			leaveTimer = null;
		}
		lastHoverTime = Date.now();
		onMouseEnter();
	}

	function handleMouseLeave() {
		const timeSinceHover = Date.now() - lastHoverTime;
		const remainingDelay = Math.max(0, hoverDelayMs - timeSinceHover);

		if (remainingDelay > 0) {
			// Delay the leave event
			leaveTimer = setTimeout(() => {
				onMouseLeave();
				leaveTimer = null;
			}, remainingDelay);
		} else {
			// No delay needed
			onMouseLeave();
		}
	}
</script>

{#if expanded}
	<!-- Expanded comment card -->
	<div
		data-comment-id={comment.id}
		class="absolute left-0 right-4 z-20 rounded-lg border-l-4 bg-white px-4 py-3 shadow-lg"
		style:top="{top}px"
		style:border-left-color={annotation.color}
		onmouseenter={handleMouseEnter}
		onmouseleave={handleMouseLeave}
		onclick={onClick}
		onkeydown={(e) => {
			if (e.key === 'Enter' || e.key === ' ') {
				e.preventDefault();
				onClick(e as any);
			}
		}}
		role="button"
		tabindex="0"
		in:fly={{ x: -20, duration: 250, easing: quintOut }}
		out:fly={{ x: -20, duration: 200, easing: quintOut }}
	>
		{#if showDeleteConfirm}
			<!-- Delete confirmation -->
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
			<!-- Normal comment display -->
			<div class="mb-2 flex items-center justify-between">
				<div class="flex items-center gap-2">
					<div
						class="h-3 w-3 rounded-full"
						style:background-color={annotation.color}
					></div>
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
				<p class="mb-2 text-xs italic text-gray-500">"{annotation.text.substring(0, 100)}{annotation.text.length > 100 ? '...' : ''}"</p>
			{/if}
			{#if comment.content}
				<p class="text-sm leading-relaxed text-gray-800">{comment.content}</p>
			{:else}
				<p class="text-xs italic text-gray-400">No comment added</p>
			{/if}
		{/if}
	</div>
{:else}
	<!-- Collapsed indicator badge -->
	<div
		data-comment-id={comment.id}
		class="absolute right-4 z-10 cursor-pointer rounded-full px-2.5 py-1 shadow-md hover:scale-105 hover:shadow-lg"
		style:top="{top}px"
		style:background-color={annotation.color}
		onmouseenter={handleMouseEnter}
		onmouseleave={handleMouseLeave}
		onclick={onClick}
		onkeydown={(e) => {
			if (e.key === 'Enter' || e.key === ' ') {
				e.preventDefault();
				onClick(e as any);
			}
		}}
		role="button"
		tabindex="0"
		title="Click to view comment"
		in:scale={{ duration: 200, start: 0.8, easing: quintOut }}
		out:scale={{ duration: 150, start: 0.8, easing: quintOut }}
	>
		<span class="text-xs font-semibold text-gray-800">
			{comment.user?.username?.[0]?.toUpperCase() ?? '?'}
		</span>
	</div>
{/if}
