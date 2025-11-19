<script lang="ts">
	import type { CommentRead } from '$api/types';
	import type { Annotation } from '$types/pdf';
	import CommentCard from './CommentCard.svelte';
	import CommentGroup from './CommentGroup.svelte';
	import { browser } from '$app/environment';

	interface Props {
		comments: CommentRead[];
		pageDataArray: Array<{ pageNumber: number; width: number; height: number }>;
		pdfContainerRef: HTMLDivElement | null;
		scrollContainerRef: HTMLDivElement | null;
		hoveredCommentId?: number | null;
		focusedCommentId?: number | null;
		onCommentDelete?: (commentId: number) => Promise<void>;
	}

	let {
		comments = [],
		pageDataArray = [],
		pdfContainerRef = null,
		scrollContainerRef = null,
		hoveredCommentId = $bindable(null),
		focusedCommentId = $bindable(null),
		onCommentDelete = async () => {}
	}: Props = $props();

	let sidebarRef: HTMLDivElement | null = $state(null);
	let deleteConfirmId = $state<number | null>(null);
	let selectedCommentInGroup = $state<{ [groupId: string]: number }>({});
	let hoveredGroupId = $state<string | null>(null);

	interface PositionedComment {
		comment: CommentRead;
		annotation: Annotation;
		idealTop: number;
		actualTop: number;
		highlightBottom: number;
		highlightRightX: number;
	}

	interface CommentGroupData {
		id: string;
		comments: CommentRead[];
		actualTop: number;
		highlightBottom: number;
		highlightRightX: number;
	}

	const COMMENT_HEIGHT = 80;
	const COMMENT_COLLAPSED_HEIGHT = 32;
	const MIN_GAP = 8;
	const GROUP_THRESHOLD = 40; // Comments within 40px are grouped

	// Get page offset from top of scroll container
	function getPageOffsetTop(pageNumber: number): number {
		if (!scrollContainerRef || !pdfContainerRef) return 0;

		const pageElement = pdfContainerRef.querySelector(`[data-page-number="${pageNumber}"]`);
		if (!pageElement) return 0;

		const scrollRect = scrollContainerRef.getBoundingClientRect();
		const pageRect = pageElement.getBoundingClientRect();

		return pageRect.top - scrollRect.top + scrollContainerRef.scrollTop;
	}

	// Get highlight position
	function getHighlightBottomPosition(
		annotation: Annotation
	): { rightX: number; bottom: number } {
		if (!annotation?.boundingBoxes || annotation.boundingBoxes.length === 0) {
			return { rightX: 0, bottom: 0 };
		}

		const pageData = pageDataArray.find((p) => p.pageNumber === annotation.pageNumber);
		if (!pageData || pageData.width === 0 || pageData.height === 0) {
			return { rightX: 0, bottom: 0 };
		}

		if (!pdfContainerRef || !sidebarRef) return { rightX: 0, bottom: 0 };

		// Find the bottommost box
		const bottomBox = annotation.boundingBoxes.reduce((prev, curr) => {
			const prevBottom = prev.y + prev.height;
			const currBottom = curr.y + curr.height;
			return currBottom > prevBottom ? curr : prev;
		});

		// Find the rightmost box
		const rightBox = annotation.boundingBoxes.reduce((prev, curr) => {
			const prevRight = prev.x + prev.width;
			const currRight = curr.x + curr.width;
			return currRight > prevRight ? curr : prev;
		});

		const pageElement = pdfContainerRef.querySelector(
			`[data-page-number="${annotation.pageNumber}"]`
		);
		if (!pageElement) return { rightX: 0, bottom: 0 };

		const pageOffsetTop = getPageOffsetTop(annotation.pageNumber);
		const sidebarRect = sidebarRef.getBoundingClientRect();
		const pageRect = pageElement.getBoundingClientRect();

		// Calculate right edge of highlight relative to sidebar
		const highlightRightWithinPage = (rightBox.x + rightBox.width) * pageData.width;
		const highlightRightX = pageRect.left - sidebarRect.left + highlightRightWithinPage;

		// Calculate bottom position
		const highlightBottom = pageOffsetTop + (bottomBox.y + bottomBox.height) * pageData.height;

		return {
			rightX: highlightRightX,
			bottom: highlightBottom
		};
	}

	// Group comments and calculate positions with collision avoidance
	let commentGroups = $derived.by((): CommentGroupData[] => {
		if (!pdfContainerRef || !sidebarRef || !scrollContainerRef || pageDataArray.length === 0) {
			return [];
		}

		// First, calculate ideal positions for all comments
		const positioned: PositionedComment[] = [];

		for (const comment of comments) {
			const annotation = comment.annotation as unknown as Annotation;
			if (!annotation?.pageNumber) continue;

			const highlightPos = getHighlightBottomPosition(annotation);
			const commentHeight = COMMENT_COLLAPSED_HEIGHT;

			positioned.push({
				comment,
				annotation,
				idealTop: highlightPos.bottom - commentHeight,
				actualTop: 0,
				highlightBottom: highlightPos.bottom,
				highlightRightX: highlightPos.rightX
			});
		}

		// Sort by ideal position
		positioned.sort((a, b) => a.idealTop - b.idealTop);

		// Group comments that are close together
		const groups: CommentGroupData[] = [];
		let currentGroup: PositionedComment[] = [];

		for (let i = 0; i < positioned.length; i++) {
			const current = positioned[i];

			if (currentGroup.length === 0) {
				currentGroup.push(current);
			} else {
				const lastInGroup = currentGroup[currentGroup.length - 1];
				// Check if current comment is close enough to group with previous
				if (Math.abs(current.idealTop - lastInGroup.idealTop) <= GROUP_THRESHOLD) {
					currentGroup.push(current);
				} else {
					// Start new group - store all positioned comments for later lookup
					groups.push({
						id: currentGroup.map((c) => c.comment.id).join('-'),
						comments: currentGroup.map((c) => c.comment),
						actualTop: 0,
						highlightBottom: 0, // Will be set based on active comment
						highlightRightX: 0  // Will be set based on active comment
					});
					currentGroup = [current];
				}
			}
		}

		// Add last group
		if (currentGroup.length > 0) {
			groups.push({
				id: currentGroup.map((c) => c.comment.id).join('-'),
				comments: currentGroup.map((c) => c.comment),
				actualTop: 0,
				highlightBottom: 0, // Will be set based on active comment
				highlightRightX: 0  // Will be set based on active comment
			});
		}

		// Set highlight positions based on active comment in each group
		for (const group of groups) {
			const activeCommentId = selectedCommentInGroup[group.id] || group.comments[0].id;
			const positionedForActive = positioned.find((p) => p.comment.id === activeCommentId);
			if (positionedForActive) {
				group.highlightBottom = positionedForActive.highlightBottom;
				group.highlightRightX = positionedForActive.highlightRightX;
			}
		}

		// Apply collision detection to groups
		for (let i = 0; i < groups.length; i++) {
			const group = groups[i];
			const isGroupExpanded =
				group.comments.some((c) => c.id === hoveredCommentId || c.id === focusedCommentId) ||
				hoveredGroupId === group.id;
			const groupHeight = isGroupExpanded ? COMMENT_HEIGHT : COMMENT_COLLAPSED_HEIGHT;

			// Calculate ideal top for group (average of all comments in group)
			const avgIdealTop =
				positioned
					.filter((p) => group.comments.some((c) => c.id === p.comment.id))
					.reduce((sum, p) => sum + p.idealTop, 0) / group.comments.length;

			if (i === 0) {
				group.actualTop = Math.max(0, avgIdealTop);
			} else {
				const prev = groups[i - 1];
				const prevIsExpanded =
					prev.comments.some((c) => c.id === hoveredCommentId || c.id === focusedCommentId) ||
					hoveredGroupId === prev.id;
				const prevHeight = prevIsExpanded ? COMMENT_HEIGHT : COMMENT_COLLAPSED_HEIGHT;
				const prevBottom = prev.actualTop + prevHeight + MIN_GAP;
				group.actualTop = Math.max(avgIdealTop, prevBottom);
			}
		}

		return groups;
	});

	// Comment interaction handlers
	function handleCommentClick(commentId: number, event: MouseEvent) {
		event.stopPropagation();
		focusedCommentId = focusedCommentId === commentId ? null : commentId;
		deleteConfirmId = null;
	}

	function handleMouseEnter(commentId: number) {
		hoveredCommentId = commentId;
	}

	function handleMouseLeave() {
		hoveredCommentId = null;
	}

	// Group interaction handlers
	function handleGroupClick(groupId: string, event: MouseEvent) {
		event.stopPropagation();
		const group = commentGroups.find((g) => g.id === groupId);
		if (!group) return;

		// If no comment is focused in this group, focus the first one
		const focusedInGroup = group.comments.find((c) => c.id === focusedCommentId);
		if (!focusedInGroup) {
			focusedCommentId = group.comments[0].id;
		} else {
			// Toggle off
			focusedCommentId = null;
		}
		deleteConfirmId = null;
	}

	function handleGroupMouseEnter(groupId: string) {
		hoveredGroupId = groupId;
		const group = commentGroups.find((g) => g.id === groupId);
		if (!group) return;

		// Set hovered to first comment in group or selected comment
		const selected = selectedCommentInGroup[groupId];
		hoveredCommentId = selected || group.comments[0].id;
	}

	function handleGroupMouseLeave() {
		hoveredGroupId = null;
		hoveredCommentId = null;
	}

	function handleDeleteClick(commentId: number, event: MouseEvent) {
		event.stopPropagation();
		deleteConfirmId = commentId;
	}

	async function handleDeleteConfirm(commentId: number, event: MouseEvent) {
		event.stopPropagation();
		await onCommentDelete(commentId);
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
		const isCommentClick = target.closest('[data-comment-id]');
		const isHighlightClick = target.closest('.annotation-group');

		if (!isCommentClick && !isHighlightClick) {
			focusedCommentId = null;
			deleteConfirmId = null;
		}
	}

	// Setup global click listener
	$effect(() => {
		if (browser) {
			document.addEventListener('click', handleDocumentClick);
			return () => {
				document.removeEventListener('click', handleDocumentClick);
			};
		}
	});
</script>

<div bind:this={sidebarRef} class="comment-sidebar relative flex-1 overflow-visible bg-gray-50 pr-4">
	{#each commentGroups as group (group.id)}
		{@const isGroupExpanded =
			group.comments.some((c) => c.id === focusedCommentId) || hoveredGroupId === group.id}
		{@const isGroupHovered = hoveredGroupId === group.id}
		{@const groupHeight = isGroupExpanded ? COMMENT_HEIGHT : COMMENT_COLLAPSED_HEIGHT}
		{@const groupBottom = group.actualTop + groupHeight}
		{@const sidebarWidth = sidebarRef?.getBoundingClientRect().width || 0}
		{@const commentLeftEdge = sidebarWidth - 16}

		{@const activeCommentId = selectedCommentInGroup[group.id] || group.comments[0].id}
		{@const activeComment = group.comments.find((c) => c.id === activeCommentId) || group.comments[0]}
		{@const activeAnnotation = activeComment.annotation as unknown as Annotation}

		<!-- Connection line (only when expanded and highlight is visible) -->
		{#if (isGroupExpanded || isGroupHovered) && group.highlightRightX > 0}
			<svg
				class="pointer-events-none absolute left-0 top-0 z-0 overflow-visible"
				style:width="{sidebarWidth + 500}px"
				style:height="{Math.max(groupBottom, group.highlightBottom) + 50}px"
			>
				<line
					x1={group.highlightRightX}
					y1={group.highlightBottom}
					x2={commentLeftEdge}
					y2={groupBottom}
					stroke={activeAnnotation.color}
					stroke-width="2"
					stroke-opacity="0.6"
				/>
			</svg>
		{/if}

		<!-- Render group or single comment -->
		{#if group.comments.length > 1}
			{@const groupSelectedId = selectedCommentInGroup[group.id] || null}
			<CommentGroup
				comments={group.comments}
				top={group.actualTop}
				{isGroupExpanded}
				{isGroupHovered}
				selectedCommentId={groupSelectedId}
				deleteConfirmId={deleteConfirmId}
				onGroupClick={(e) => handleGroupClick(group.id, e)}
				onGroupMouseEnter={() => handleGroupMouseEnter(group.id)}
				onGroupMouseLeave={handleGroupMouseLeave}
				onCommentSelect={(commentId) => {
					selectedCommentInGroup[group.id] = commentId;
					hoveredCommentId = commentId;
				}}
				onDeleteClick={handleDeleteClick}
				onDeleteConfirm={handleDeleteConfirm}
				onDeleteCancel={handleDeleteCancel}
			/>
		{:else}
			{@const comment = group.comments[0]}
			{@const annotation = comment.annotation as unknown as Annotation}
			{@const expanded = hoveredCommentId === comment.id || focusedCommentId === comment.id}
			{@const showDeleteConfirm = deleteConfirmId === comment.id}

			<CommentCard
				{comment}
				{annotation}
				{expanded}
				{showDeleteConfirm}
				top={group.actualTop}
				onClick={(e) => handleCommentClick(comment.id, e)}
				onMouseEnter={() => handleMouseEnter(comment.id)}
				onMouseLeave={handleMouseLeave}
				onDeleteClick={(e) => handleDeleteClick(comment.id, e)}
				onDeleteConfirm={(e) => handleDeleteConfirm(comment.id, e)}
				onDeleteCancel={handleDeleteCancel}
			/>
		{/if}
	{/each}
</div>

<style>
	.comment-sidebar {
		min-height: 100%;
	}
</style>
