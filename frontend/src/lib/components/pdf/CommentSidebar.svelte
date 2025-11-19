<script lang="ts">
	import type { CommentRead } from '$api/types';
	import type { Annotation } from '$types/pdf';
	import CommentCard from './CommentCard.svelte';
	import CommentGroup from './CommentGroup.svelte';
	import { browser } from '$app/environment';
	import { draw } from 'svelte/transition';
	import { quintOut } from 'svelte/easing';

	interface Props {
		comments: CommentRead[];
		pageDataArray: Array<{ pageNumber: number; width: number; height: number }>;
		pdfContainerRef: HTMLDivElement | null;
		scrollContainerRef: HTMLDivElement | null;
		hoveredCommentId?: number | null;
		focusedCommentId?: number | null;
		hoverDelayMs?: number;
		onCommentDelete?: (commentId: number) => Promise<void>;
	}

	let {
		comments = [],
		pageDataArray = [],
		pdfContainerRef = null,
		scrollContainerRef = null,
		hoveredCommentId = $bindable(null),
		focusedCommentId = $bindable(null),
		hoverDelayMs = 200,
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
		highlightTop: number;
		highlightBottom: number;
		highlightLeftX: number;
		highlightRightX: number;
	}

	interface CommentGroupData {
		id: string;
		comments: CommentRead[];
		actualTop: number;
		highlightTop: number;
		highlightBottom: number;
		highlightLeftX: number;
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
	function getHighlightPosition(annotation: Annotation): {
		leftX: number;
		rightX: number;
		top: number;
		bottom: number;
	} {
		if (!annotation?.boundingBoxes || annotation.boundingBoxes.length === 0) {
			return { leftX: 0, rightX: 0, top: 0, bottom: 0 };
		}

		const pageData = pageDataArray.find((p) => p.pageNumber === annotation.pageNumber);
		if (!pageData || pageData.width === 0 || pageData.height === 0) {
			return { leftX: 0, rightX: 0, top: 0, bottom: 0 };
		}

		if (!pdfContainerRef || !sidebarRef) return { leftX: 0, rightX: 0, top: 0, bottom: 0 };

		// Find the topmost box
		const topBox = annotation.boundingBoxes.reduce((prev, curr) => {
			return curr.y < prev.y ? curr : prev;
		});

		// Find the bottommost box
		const bottomBox = annotation.boundingBoxes.reduce((prev, curr) => {
			const prevBottom = prev.y + prev.height;
			const currBottom = curr.y + curr.height;
			return currBottom > prevBottom ? curr : prev;
		});

		// Find the leftmost box
		const leftBox = annotation.boundingBoxes.reduce((prev, curr) => {
			return curr.x < prev.x ? curr : prev;
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
		if (!pageElement) return { leftX: 0, rightX: 0, top: 0, bottom: 0 };

		const pageOffsetTop = getPageOffsetTop(annotation.pageNumber);
		const sidebarRect = sidebarRef.getBoundingClientRect();
		const pageRect = pageElement.getBoundingClientRect();

		// Calculate left edge of highlight relative to sidebar
		const highlightLeftWithinPage = leftBox.x * pageData.width;
		const highlightLeftX = pageRect.left - sidebarRect.left + highlightLeftWithinPage;

		// Calculate right edge of highlight relative to sidebar
		const highlightRightWithinPage = (rightBox.x + rightBox.width) * pageData.width;
		const highlightRightX = pageRect.left - sidebarRect.left + highlightRightWithinPage;

		// Calculate top position
		const highlightTop = pageOffsetTop + topBox.y * pageData.height;

		// Calculate bottom position
		const highlightBottom = pageOffsetTop + (bottomBox.y + bottomBox.height) * pageData.height;

		return {
			leftX: highlightLeftX,
			rightX: highlightRightX,
			top: highlightTop,
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

			const highlightPos = getHighlightPosition(annotation);

			positioned.push({
				comment,
				annotation,
				idealTop: highlightPos.top,
				actualTop: 0,
				highlightTop: highlightPos.top,
				highlightBottom: highlightPos.bottom,
				highlightLeftX: highlightPos.leftX,
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
						highlightTop: 0, // Will be set based on active comment
						highlightBottom: 0, // Will be set based on active comment
						highlightLeftX: 0, // Will be set based on active comment
						highlightRightX: 0 // Will be set based on active comment
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
				highlightTop: 0, // Will be set based on active comment
				highlightBottom: 0, // Will be set based on active comment
				highlightLeftX: 0, // Will be set based on active comment
				highlightRightX: 0 // Will be set based on active comment
			});
		}

		// Set highlight positions based on active comment in each group
		// This will be recalculated in the template based on hoveredCommentId
		for (const group of groups) {
			// Just set defaults here, actual position determined by active comment in template
			const firstPositioned = positioned.find((p) => p.comment.id === group.comments[0].id);
			if (firstPositioned) {
				group.highlightTop = firstPositioned.highlightTop;
				group.highlightBottom = firstPositioned.highlightBottom;
				group.highlightLeftX = firstPositioned.highlightLeftX;
				group.highlightRightX = firstPositioned.highlightRightX;
			}
		}

		// Store positioned data for later lookup
		groups.forEach((g) => {
			(g as any).positionedData = positioned.filter((p) =>
				g.comments.some((c) => c.id === p.comment.id)
			);
		});

		// Apply collision detection to groups
		for (let i = 0; i < groups.length; i++) {
			const group = groups[i];

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

<div
	bind:this={sidebarRef}
	class="comment-sidebar relative flex-1 overflow-visible bg-gray-50 pr-2"
>
	{#each commentGroups as group (group.id)}
		{@const isGroupExpanded =
			group.comments.some((c) => c.id === focusedCommentId) ||
			group.comments.some((c) => c.id === hoveredCommentId) ||
			hoveredGroupId === group.id}
		{@const isGroupHovered =
			hoveredGroupId === group.id || group.comments.some((c) => c.id === hoveredCommentId)}
		{@const sidebarWidth = sidebarRef?.getBoundingClientRect().width || 0}
		{@const commentLeftEdge = sidebarWidth - 8}

		{@const activeCommentId =
			hoveredCommentId && group.comments.some((c) => c.id === hoveredCommentId)
				? hoveredCommentId
				: selectedCommentInGroup[group.id] || group.comments[0].id}
		{@const activeComment =
			group.comments.find((c) => c.id === activeCommentId) || group.comments[0]}
		{@const activeAnnotation = activeComment.annotation as unknown as Annotation}

		{@const activePositioned = (group as any).positionedData?.find(
			(p: any) => p.comment.id === activeCommentId
		)}
		{@const activeHighlightTop = activePositioned?.highlightTop || group.highlightTop}
		{@const activeHighlightLeftX = activePositioned?.highlightLeftX || group.highlightLeftX}

		<!-- Connection line (only when expanded and highlight is visible) -->
		{#if (isGroupExpanded || isGroupHovered) && activeHighlightLeftX > 0}
			{@const isFocused = group.comments.some((c) => c.id === focusedCommentId)}
			<svg
				class="pointer-events-none absolute top-0 left-0 z-10 overflow-visible transition-all duration-300"
				style:width="{sidebarWidth + 500}px"
				style:height="{Math.max(group.actualTop, activeHighlightTop) + 50}px"
				style:filter={isFocused
					? 'drop-shadow(0 2px 6px rgba(0, 0, 0, 0.2))'
					: 'drop-shadow(0 1px 3px rgba(0, 0, 0, 0.1))'}
			>
				<line
					x1={activeHighlightLeftX}
					y1={activeHighlightTop}
					x2={commentLeftEdge}
					y2={group.actualTop}
					stroke={activeAnnotation.color}
					stroke-width={isFocused ? '4' : '3'}
					stroke-opacity={isFocused ? '0.9' : '0.7'}
					class="transition-all duration-300"
					in:draw={{ duration: 300, easing: quintOut }}
					out:draw={{ duration: 200, easing: quintOut }}
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
				{deleteConfirmId}
				{hoverDelayMs}
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
				{hoverDelayMs}
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
		position: relative;
	}

	/* Ensure connection lines can extend beyond sidebar bounds */
	.comment-sidebar :global(svg) {
		overflow: visible;
	}
</style>
