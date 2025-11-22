<script lang="ts">
	import type { CommentRead } from '$api/types';
	import type { Annotation } from '$types/pdf';

	interface Props {
		comments: CommentRead[];
		pageNumber: number;
		width: number;
		height: number;
		hoveredCommentId: number | null;
		focusedCommentId: number | null;
	}

	let {
		comments = [],
		pageNumber,
		width,
		height,
		hoveredCommentId,
		focusedCommentId
	}: Props = $props();

	// Filter comments for current page
	let pageComments = $derived(
		comments.filter((c) => {
			const annotation = c.annotation as unknown as Annotation;
			return annotation?.pageNumber === pageNumber;
		})
	);

	import { commentStore } from '$lib/stores/commentStore';
	import { computeScaledBoundingBoxes } from '$lib/util/positionUtils';

	// Svelte action that registers a highlight element for a comment id.
	function registerHighlight(node: HTMLElement, commentId?: number) {
		if (!commentId) return;
		commentStore.registerAnnotationHighlightElement(commentId, node);
		return {
			destroy() {
				commentStore.registerAnnotationHighlightElement(commentId, null);
			}
		};
	}
</script>

{#if width > 0 && height > 0}
	<div class="annotations-layer pointer-events-none absolute left-0 top-0 h-full w-full">
		{#each pageComments as comment (comment.id)}
			{@const annotation = comment.annotation as unknown as Annotation}
			{@const scaledBoxes = computeScaledBoundingBoxes(
				annotation,
				{ pageNumber: pageNumber, width, height },
				1
			)}
			{@const isHovered = hoveredCommentId === comment.id}
			{@const isFocused = focusedCommentId === comment.id}
			{@const isActive = isHovered || isFocused}

			{@const topBoxIndex = scaledBoxes.reduce(
				(minIdx, b, idx) => (b.y < scaledBoxes[minIdx].y ? idx : minIdx),
				0
			)}
			<div class="annotation-group pointer-events-none">
				{#each scaledBoxes as box, boxIdx (`${comment.id}-${boxIdx}`)}
					{@const MARGIN = 1}
					<div
						class="absolute rounded-sm"
						style:left="{box.x - MARGIN}px"
						style:top="{box.y - MARGIN}px"
						style:width="{box.width + MARGIN * 2}px"
						style:height="{box.height + MARGIN * 2}px"
						style:background-color={annotation.color}
						style:opacity={isActive ? "0.5" : "0.3"}
						style:border={isActive ? `2px solid ${annotation.color}` : "none"}
						style:box-shadow={isFocused
							? `0 4px 12px rgba(0, 0, 0, 0.15), 0 0 0 3px ${annotation.color}40`
							: isHovered
								? "0 2px 8px rgba(0, 0, 0, 0.1)"
								: "none"}
						style:box-sizing="border-box"
						use:registerHighlight={boxIdx === topBoxIndex ? comment.id : undefined}
					></div>
				{/each}
			</div>
		{/each}
	</div>
{/if}
