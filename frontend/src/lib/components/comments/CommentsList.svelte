<script lang="ts">
	import type { CommentRead } from '$api/types.js';
	import type { Annotation } from '$types/pdf';
	import SingleComment from './SingleComment.svelte';

	interface PositionedComment {
		comment: CommentRead;
		idealTop: number;
		actualTop: number;
		highlightBottom: number; // Bottom position of highlight for line connection
		highlightRightX: number; // Horizontal position of highlight right edge (pixels from left of viewport)
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

	// Reference to the comments section container for positioning calculations
	let commentsSectionRef: HTMLDivElement | null = $state(null);

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

	// Calculate ideal vertical position for a comment (bottom-aligned with highlight)
	function getIdealCommentTopPosition(comment: CommentRead, commentHeight: number): number {
		const annotation = comment.annotation as unknown as Annotation;
		if (!annotation || !annotation.boundingBoxes || annotation.boundingBoxes.length === 0) {
			return 0;
		}

		const pageData = getPageDimensions(annotation.pageNumber);
		if (pageData.height === 0) return 0;

		// Find the bottommost bounding box (highest y + height)
		const bottomBox = annotation.boundingBoxes.reduce((prev, curr) => {
			const prevBottom = prev.y + prev.height;
			const currBottom = curr.y + curr.height;
			return currBottom > prevBottom ? curr : prev;
		});

		// Convert normalized position to pixels within the page (bottom of highlight)
		const bottomPositionInPage = (bottomBox.y + bottomBox.height) * pageData.height;

		// Get the page's offset from top of viewer
		const pageOffsetTop = getPageOffsetTop(annotation.pageNumber);

		// Calculate top position so comment bottom aligns with highlight bottom
		const highlightBottom = pageOffsetTop + bottomPositionInPage;
		return highlightBottom - commentHeight;
	}

	// Get the bottom-right position of the highlight (for line connection start)
	// Returns position relative to the comments section container
	function getHighlightBottomPosition(
		comment: CommentRead,
		commentsSectionRef: HTMLElement | null
	): { rightX: number; bottom: number } {
		const annotation = comment.annotation as unknown as Annotation;
		if (!annotation || !annotation.boundingBoxes || annotation.boundingBoxes.length === 0) {
			return { rightX: 0, bottom: 0 };
		}

		const pageData = getPageDimensions(annotation.pageNumber);
		if (pageData.width === 0 || pageData.height === 0) return { rightX: 0, bottom: 0 };

		if (!documentScrollRef || !pdfContainerRef || !commentsSectionRef)
			return { rightX: 0, bottom: 0 };

		// Find the bottommost bounding box (for vertical position)
		const bottomBox = annotation.boundingBoxes.reduce((prev, curr) => {
			const prevBottom = prev.y + prev.height;
			const currBottom = curr.y + curr.height;
			return currBottom > prevBottom ? curr : prev;
		});

		// Find the rightmost bounding box (for horizontal position)
		const rightBox = annotation.boundingBoxes.reduce((prev, curr) => {
			const prevRight = prev.x + prev.width;
			const currRight = curr.x + curr.width;
			return currRight > prevRight ? curr : prev;
		});

		// Get the page element to calculate absolute horizontal position
		const pageElement = pdfContainerRef.querySelector(
			`[data-page-number="${annotation.pageNumber}"]`
		);
		if (!pageElement) return { rightX: 0, bottom: 0 };

		const pageOffsetTop = getPageOffsetTop(annotation.pageNumber);

		// Get viewport positions
		const commentsRect = commentsSectionRef.getBoundingClientRect();
		const pageRect = pageElement.getBoundingClientRect();

		// Calculate horizontal position relative to comments section's left edge
		const highlightRightWithinPage = (rightBox.x + rightBox.width) * pageData.width;
		const highlightRightX = pageRect.left - commentsRect.left + highlightRightWithinPage;

		// Return absolute position
		return {
			rightX: highlightRightX,
			bottom: pageOffsetTop + (bottomBox.y + bottomBox.height) * pageData.height
		};
	}

	// Calculate non-overlapping positions for all comments
	let positionedComments = $derived.by((): PositionedComment[] => {
		if (!documentScrollRef || !pdfContainerRef || !commentsSectionRef || pageDataArray.length === 0)
			return [];

		const COMMENT_HEIGHT = 60;
		const MIN_GAP = 8;

		// Calculate ideal positions for all comments
		const sorted = comments
			.map((comment) => {
				const highlightPos = getHighlightBottomPosition(comment, commentsSectionRef);
				return {
					comment,
					idealTop: getIdealCommentTopPosition(comment, COMMENT_HEIGHT),
					actualTop: 0,
					highlightBottom: highlightPos.bottom,
					highlightRightX: highlightPos.rightX
				};
			})
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

<div class="relative overflow-visible" bind:this={commentsSectionRef}>
	{#each positionedComments as { comment, actualTop, idealTop, highlightBottom, highlightRightX } (comment.id)}
		{@const annotation = comment.annotation as unknown as Annotation}
		{@const expanded = isCommentExpanded(comment.id)}
		{@const showDeleteConfirm = deleteConfirmId === comment.id}
		{@const COMMENT_HEIGHT = 60}
		{@const commentBottom = actualTop + COMMENT_HEIGHT}
		{@const needsVerticalLine = actualTop !== idealTop}
		{@const horizontalLineY = highlightBottom}
		{@const commentsSectionWidth = commentsSectionRef?.getBoundingClientRect().width || 0}
		{@const verticalLineX = commentsSectionWidth}
		{@const commentLeftEdge = commentsSectionWidth - 12}

		<!-- Connection line from highlight to comment (only when expanded) -->
		{#if expanded && highlightRightX > 0}
			<svg
				class="pointer-events-none absolute top-0 left-0 z-50 overflow-visible"
				style:width="200vw"
				style:height="{Math.max(commentBottom, horizontalLineY) + 20}px"
			>
				<!-- Horizontal line from highlight to right edge of comments section -->
				<line
					x1={highlightRightX}
					y1={horizontalLineY}
					x2={verticalLineX}
					y2={horizontalLineY}
					stroke={annotation.color}
					stroke-width="1.5"
					stroke-opacity="0.5"
				/>

				<!-- Vertical line if comment was pushed down/up -->
				{#if needsVerticalLine}
					<line
						x1={verticalLineX}
						y1={horizontalLineY}
						x2={verticalLineX}
						y2={commentBottom}
						stroke={annotation.color}
						stroke-width="1.5"
						stroke-opacity="0.5"
					/>
					<!-- Final horizontal line to comment -->
					<line
						x1={verticalLineX}
						y1={commentBottom}
						x2={commentLeftEdge}
						y2={commentBottom}
						stroke={annotation.color}
						stroke-width="1.5"
						stroke-opacity="0.5"
					/>
				{:else}
					<!-- Direct horizontal line to comment (no vertical needed) -->
					<line
						x1={verticalLineX}
						y1={horizontalLineY}
						x2={commentLeftEdge}
						y2={horizontalLineY}
						stroke={annotation.color}
						stroke-width="1.5"
						stroke-opacity="0.5"
					/>
				{/if}
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
