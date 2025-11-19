<script lang="ts">
	import type { CommentRead, CommentCreate, CommentUpdate } from '$api/types';
	import type { Annotation } from '$types/pdf';
	import CommentBody from './CommentBody.svelte';
	import { fly, scale } from 'svelte/transition';
	import { quintOut } from 'svelte/easing';

	interface Props {
		comment: CommentRead;
		annotation: Annotation;
		expanded: boolean;
		showDeleteConfirm: boolean;
		top: number;
		currentUserId?: number | null;
		documentId?: string;
		hoverDelayMs?: number;
		onClick?: (event: MouseEvent) => void;
		onMouseEnter?: () => void;
		onMouseLeave?: () => void;
		onDeleteClick?: (event: MouseEvent) => void;
		onDeleteConfirm?: (event: MouseEvent) => void;
		onDeleteCancel?: (event: MouseEvent) => void;
		onUpdate?: (commentId: number, data: CommentUpdate) => Promise<void>;
		onCreate?: (data: CommentCreate) => Promise<void>;
	}

	let {
		comment,
		annotation,
		expanded,
		showDeleteConfirm,
		top,
		currentUserId = null,
		documentId = '',
		hoverDelayMs = 800,
		onClick = () => {},
		onMouseEnter = () => {},
		onMouseLeave = () => {},
		onDeleteClick = () => {},
		onDeleteConfirm = () => {},
		onDeleteCancel = () => {},
		onUpdate = async () => {},
		onCreate = async () => {}
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
		class="absolute right-2 left-4 z-20 rounded-lg border-l-4 bg-white px-4 py-3 shadow-lg"
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
		<CommentBody
			{comment}
			{annotation}
			{showDeleteConfirm}
			{currentUserId}
			{documentId}
			isExpanded={expanded}
			{onDeleteClick}
			{onDeleteConfirm}
			{onDeleteCancel}
			{onUpdate}
			{onCreate}
		/>
	</div>
{:else}
	<!-- Collapsed indicator badge -->
	<div
		data-comment-id={comment.id}
		class="absolute right-2 z-10 cursor-pointer rounded-full px-2.5 py-1 shadow-md hover:scale-105 hover:shadow-lg"
		style:left="auto"
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
