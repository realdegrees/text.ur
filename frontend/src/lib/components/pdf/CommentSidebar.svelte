<script lang="ts">
	import type { CommentRead } from '$api/types';
	import type { Annotation } from '$types/pdf';
	import CommentCard from './CommentCard.svelte';
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

	interface PositionedComment {
		comment: CommentRead;
		annotation: Annotation;
		idealTop: number;
		actualTop: number;
		highlightBottom: number;
		highlightRightX: number;
	}

	const COMMENT_HEIGHT = 80;
	const COMMENT_COLLAPSED_HEIGHT = 32;
	const MIN_GAP = 8;

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

	// Calculate positioned comments with collision avoidance
	let positionedComments = $derived.by((): PositionedComment[] => {
		if (!pdfContainerRef || !sidebarRef || !scrollContainerRef || pageDataArray.length === 0) {
			return [];
		}

		const positioned: PositionedComment[] = [];

		for (const comment of comments) {
			const annotation = comment.annotation as unknown as Annotation;
			if (!annotation?.pageNumber) continue;

			const highlightPos = getHighlightBottomPosition(annotation);
			const isExpanded = hoveredCommentId === comment.id || focusedCommentId === comment.id;
			const commentHeight = isExpanded ? COMMENT_HEIGHT : COMMENT_COLLAPSED_HEIGHT;

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

		// Apply collision detection
		for (let i = 0; i < positioned.length; i++) {
			const current = positioned[i];
			const isExpanded = hoveredCommentId === current.comment.id || focusedCommentId === current.comment.id;
			const commentHeight = isExpanded ? COMMENT_HEIGHT : COMMENT_COLLAPSED_HEIGHT;

			if (i === 0) {
				current.actualTop = Math.max(0, current.idealTop);
			} else {
				const prev = positioned[i - 1];
				const prevIsExpanded = hoveredCommentId === prev.comment.id || focusedCommentId === prev.comment.id;
				const prevHeight = prevIsExpanded ? COMMENT_HEIGHT : COMMENT_COLLAPSED_HEIGHT;
				const prevBottom = prev.actualTop + prevHeight + MIN_GAP;
				current.actualTop = Math.max(current.idealTop, prevBottom);
			}
		}

		return positioned;
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
	{#each positionedComments as { comment, annotation, actualTop, highlightBottom, highlightRightX } (comment.id)}
		{@const expanded = hoveredCommentId === comment.id || focusedCommentId === comment.id}
		{@const showDeleteConfirm = deleteConfirmId === comment.id}
		{@const commentHeight = expanded ? COMMENT_HEIGHT : COMMENT_COLLAPSED_HEIGHT}
		{@const commentBottom = actualTop + commentHeight}
		{@const sidebarWidth = sidebarRef?.getBoundingClientRect().width || 0}
		{@const commentLeftEdge = sidebarWidth - 16}

		<!-- Connection line (only when expanded and highlight is visible) -->
		{#if expanded && highlightRightX > 0}
			<svg
				class="pointer-events-none absolute left-0 top-0 z-0 overflow-visible"
				style:width="{sidebarWidth + 500}px"
				style:height="{Math.max(commentBottom, highlightBottom) + 50}px"
			>
				<line
					x1={highlightRightX}
					y1={highlightBottom}
					x2={commentLeftEdge}
					y2={commentBottom}
					stroke={annotation.color}
					stroke-width="2"
					stroke-opacity="0.6"
				/>
			</svg>
		{/if}

		<!-- Comment Card -->
		<CommentCard
			{comment}
			{annotation}
			{expanded}
			{showDeleteConfirm}
			top={actualTop}
			onClick={(e) => handleCommentClick(comment.id, e)}
			onMouseEnter={() => handleMouseEnter(comment.id)}
			onMouseLeave={handleMouseLeave}
			onDeleteClick={(e) => handleDeleteClick(comment.id, e)}
			onDeleteConfirm={(e) => handleDeleteConfirm(comment.id, e)}
			onDeleteCancel={handleDeleteCancel}
		/>
	{/each}
</div>

<style>
	.comment-sidebar {
		min-height: 100%;
	}
</style>
