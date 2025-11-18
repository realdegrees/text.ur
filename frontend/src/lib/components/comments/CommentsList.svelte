<script lang="ts">
	import type { CommentRead } from '$api/types.js';
	import type { Annotation } from '$types/pdf';
	import SingleComment from './SingleComment.svelte';

	interface PositionedComment {
		comment: CommentRead;
		idealTop: number;
		actualTop: number;
		rightEdge: number;
	}

	let {
		comments = [],
		documentScrollRef,
		pdfContainerRef,
		pageDataArray = [],
		focusedCommentId = $bindable(null),
		hoveredCommentId = $bindable(null),
		deleteConfirmId = $bindable(null),
		onDelete
	}: {
		comments: CommentRead[];
		documentScrollRef: HTMLDivElement | null;
		pdfContainerRef: HTMLDivElement | null;
		pageDataArray: Array<{ pageNumber: number; width: number; height: number }>;
		focusedCommentId: number | null;
		hoveredCommentId: number | null;
		deleteConfirmId: number | null;
		onDelete: (commentId: number) => Promise<void>;
	} = $props();

	// Calculate total height to match PDF container content
	let totalHeight = $derived.by(() => {
		if (!pdfContainerRef) return 0;
		// Get the actual height of the PDF container's content
		return pdfContainerRef.scrollHeight;
	});

	// Get page dimensions by page number
	function getPageDimensions(pageNumber: number) {
		const pageData = pageDataArray.find((p) => p.pageNumber === pageNumber);
		return pageData || { width: 0, height: 0 };
	}

	// Get page container offset from top of document scroll container
	function getPageOffsetTop(pageNumber: number): number {
		if (!documentScrollRef || !pdfContainerRef) return 0;

		const pageElement = pdfContainerRef.querySelector(`[data-page-number="${pageNumber}"]`);
		if (!pageElement) return 0;

		const scrollRect = documentScrollRef.getBoundingClientRect();
		const pageRect = pageElement.getBoundingClientRect();

		// Calculate offset from top of document scroll container (accounting for scroll)
		return pageRect.top - scrollRect.top + documentScrollRef.scrollTop;
	}

	// Check if a comment should be expanded
	function isCommentExpanded(commentId: number): boolean {
		return focusedCommentId === commentId || hoveredCommentId === commentId;
	}

	// Calculate ideal vertical position for a comment (absolute position in entire viewer)
	function getIdealCommentTopPosition(comment: CommentRead): number {
		const annotation = comment.annotation as unknown as Annotation;
		if (!annotation || !annotation.boundingBoxes || annotation.boundingBoxes.length === 0) {
			return 0;
		}

		const pageData = getPageDimensions(annotation.pageNumber);
		if (pageData.height === 0) return 0;

		// Find the topmost bounding box
		const topBox = annotation.boundingBoxes.reduce((prev, curr) => {
			return curr.y < prev.y ? curr : prev;
		});

		// Convert normalized position to pixels within the page
		const topPositionInPage = topBox.y * pageData.height;

		// Get the page's offset from top of viewer
		const pageOffsetTop = getPageOffsetTop(annotation.pageNumber);

		// Return absolute position in viewer
		return pageOffsetTop + topPositionInPage;
	}

	// Get the right edge position of the highlight (for line connection)
	function getHighlightRightEdge(comment: CommentRead): number {
		const annotation = comment.annotation as unknown as Annotation;
		if (!annotation || !annotation.boundingBoxes || annotation.boundingBoxes.length === 0) {
			return 0;
		}

		const pageData = getPageDimensions(annotation.pageNumber);
		if (pageData.width === 0) return 0;

		// Find the rightmost bounding box
		const rightBox = annotation.boundingBoxes.reduce((prev, curr) => {
			const prevRight = prev.x + prev.width;
			const currRight = curr.x + curr.width;
			return currRight > prevRight ? curr : prev;
		});

		// Convert normalized position to pixels
		return (rightBox.x + rightBox.width) * pageData.width;
	}

	// Calculate non-overlapping positions for all comments
	let positionedComments = $derived.by((): PositionedComment[] => {
		if (!documentScrollRef || !pdfContainerRef || pageDataArray.length === 0) return [];

		const COMMENT_HEIGHT = 60;
		const MIN_GAP = 8;

		// Calculate ideal positions for all comments
		const sorted = comments
			.map((comment) => ({
				comment,
				idealTop: getIdealCommentTopPosition(comment),
				actualTop: 0,
				rightEdge: getHighlightRightEdge(comment)
			}))
			.sort((a, b) => a.idealTop - b.idealTop);

		// Apply overlap protection
		for (let i = 0; i < sorted.length; i++) {
			if (i === 0) {
				sorted[i].actualTop = sorted[i].idealTop;
			} else {
				const prevBottom = sorted[i - 1].actualTop + COMMENT_HEIGHT + MIN_GAP;
				sorted[i].actualTop = Math.max(sorted[i].idealTop, prevBottom);
			}
		}

		return sorted;
	});

	function handleCommentClick(commentId: number, event: MouseEvent) {
		event.stopPropagation();
		focusedCommentId = focusedCommentId === commentId ? null : commentId;
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
		await onDelete(commentId);
		focusedCommentId = null;
		hoveredCommentId = null;
		deleteConfirmId = null;
	}

	function handleDeleteCancel(event: MouseEvent) {
		event.stopPropagation();
		deleteConfirmId = null;
	}
</script>

<div class="relative">
	{#each positionedComments as { comment, actualTop, idealTop } (comment.id)}
		{@const annotation = comment.annotation as unknown as Annotation}
		{@const expanded = isCommentExpanded(comment.id)}
		{@const showDeleteConfirm = deleteConfirmId === comment.id}

		<!-- Connection line from highlight to comment (only when expanded) -->
		{#if expanded}
			<svg
				class="pointer-events-none absolute left-0 top-0"
				style:width="100%"
				style:height="{Math.max(actualTop + 30, idealTop + 30)}px"
			>
				<line
					x1="100%"
					y1="{idealTop + 12}px"
					x2="calc(100% - 12px)"
					y2="{actualTop + 12}px"
					stroke={annotation.color}
					stroke-width="1.5"
					stroke-opacity="0.5"
				/>
			</svg>
		{/if}

		<SingleComment
			{comment}
			{annotation}
			{expanded}
			{showDeleteConfirm}
			{actualTop}
			onCommentClick={(e) => handleCommentClick(comment.id, e)}
			onMouseEnter={() => handleMouseEnter(comment.id)}
			onMouseLeave={handleMouseLeave}
			onDeleteClick={(e) => handleDeleteClick(comment.id, e)}
			onDeleteConfirm={(e) => handleDeleteConfirm(comment.id, e)}
			onDeleteCancel={handleDeleteCancel}
		/>
	{/each}
</div>
