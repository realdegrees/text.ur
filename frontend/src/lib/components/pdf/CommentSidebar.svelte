<script lang="ts">
	import type { CommentRead } from '$api/types';
	import { commentStore } from '$lib/stores/commentStore';
	import type { CommentGroup as CommentGroupData } from '$lib/stores/commentStore';
	import CommentGroup from './CommentGroup.svelte';
	import { browser } from '$app/environment';

	interface Props {
		comments: CommentRead[];
		cssScaleFactor?: number;
		documentScrollTop?: number;
		isDragging: boolean;
		hoveredCommentId?: number | null;
		focusedCommentId?: number | null;
		hoverDelayMs?: number;
	}

	let {
		comments = [],
		cssScaleFactor = 1,
		documentScrollTop = 0,
		isDragging = false,
		hoveredCommentId = $bindable(null),
		focusedCommentId = $bindable(null),
		hoverDelayMs = 200
	}: Props = $props();

	let sidebarRef: HTMLDivElement | null = $state(null);
	let deleteConfirmId = $state<number | null>(null);
	let selectedCommentInGroup = $state<{ [groupId: string]: number }>({});

	// Subscribe to computed groups from store
	let commentGroups = $state<CommentGroupData[]>([]);
	$effect(() => {
		const unsubscribe = commentStore.subscribeToGroups((groups) => {
			commentGroups = groups;
		});
		return unsubscribe;
	});

	// Group interaction handlers
	function handleGroupClick(groupId: string, event: MouseEvent) {
		event.stopPropagation();
		const group = commentGroups.find((g) => g.id === groupId);
		if (!group) return;

		// Find actual comments from group IDs
		const groupComments = comments.filter((c) => group.commentIds.includes(c.id));

		// If no comment is focused in this group, focus the first one
		const focusedInGroup = groupComments.find((c) => c.id === focusedCommentId);
		if (!focusedInGroup) {
			focusedCommentId = groupComments[0]?.id ?? null;
		} else {
			// Toggle off
			focusedCommentId = null;
		}
		deleteConfirmId = null;
	}

	function handleGroupMouseEnter(groupId: string) {
		// Don't expand comments during divider dragging
		if (isDragging) return;

		const group = commentGroups.find((g) => g.id === groupId);
		if (!group) return;

		// Set hovered to first comment in group or selected comment
		const selected = selectedCommentInGroup[groupId];
		hoveredCommentId = selected || group.commentIds[0];
	}

	function handleGroupMouseLeave() {
		hoveredCommentId = null;
	}

	function handleDeleteClick(commentId: number, event: MouseEvent) {
		event.stopPropagation();
		deleteConfirmId = commentId;
	}

	async function handleDeleteConfirm(commentId: number, event: MouseEvent) {
		event.stopPropagation();
		await commentStore.delete(commentId);
		focusedCommentId = null;
		hoveredCommentId = null;
		deleteConfirmId = null;
	}

	function handleDeleteCancel(event: MouseEvent) {
		event.stopPropagation();
		deleteConfirmId = null;
	}

	// Handle clicks outside comments
	function handleDocumentClick(event: MouseEvent) {
		const target = event.target as HTMLElement;

		// If the click occurred inside the sidebar, treat it as a comment click
		const isCommentClick = sidebarRef?.contains(target) ?? false;

		// If click occurred inside a highlight, find the comment by highlight element
		const highlightId = commentStore.findCommentByHighlightElement(target);
		const isHighlightClick = highlightId !== null;

		if (!isCommentClick && !isHighlightClick) {
			focusedCommentId = null;
			deleteConfirmId = null;
		}
	}

	// Setup global click listener
	$effect(() => {
		// Make effect re-run on deps
		void cssScaleFactor;
		void documentScrollTop;

		if (browser) {
			document.addEventListener('click', handleDocumentClick);
			return () => {
				document.removeEventListener('click', handleDocumentClick);
			};
		}
	});
</script>

<div
	bind:this={sidebarRef}
	class="comment-sidebar relative flex-1 overflow-visible bg-background pr-2"
>
	{#each commentGroups as group (group.id)}
		{@const groupComments = comments.filter((c) => group.commentIds.includes(c.id))}
		{@const expanded = group.isExpanded || group.isHovered}
		{@const hovered = group.isHovered}
		{@const activeCommentId = group.activeCommentId}

		<div bind:this={group.element}>
		<!-- Render comment group -->
		<CommentGroup
			
			comments={groupComments}
			top={group.actualTop}
			{expanded}
			{hovered}
			selectedCommentId={activeCommentId}
			{deleteConfirmId}
			{hoverDelayMs}
			{cssScaleFactor}
			sidebarRef={sidebarRef}
			{hoveredCommentId}
			selectedInGroup={selectedCommentInGroup[group.id]}
			onClick={(e: MouseEvent) => handleGroupClick(group.id, e)}
			onMouseEnter={() => handleGroupMouseEnter(group.id)}
			onMouseLeave={handleGroupMouseLeave}
			onCommentSelect={(commentId: number) => {
				selectedCommentInGroup[group.id] = commentId;
				hoveredCommentId = commentId;
			}}
			onDeleteClick={handleDeleteClick}
			onDeleteConfirm={handleDeleteConfirm}
			onDeleteCancel={handleDeleteCancel}
		/>
		</div>
	{/each}
</div>

<style>
	.comment-sidebar {
		min-height: 100%;
		position: relative;
	}

	/* Ensure connection lines can extend beyond sidebar bounds */
	.comment-sidebar :global(svg) {
		overflow: visible;
	}
</style>
