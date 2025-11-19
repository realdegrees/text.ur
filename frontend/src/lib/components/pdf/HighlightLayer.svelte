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
</script>

{#if width > 0 && height > 0}
	<div class="annotations-layer pointer-events-none absolute top-0 left-0 h-full w-full">
		{#each pageComments as comment (comment.id)}
			{@const annotation = comment.annotation as unknown as Annotation}
			{@const scaledBoxes = annotation.boundingBoxes.map((box) => ({
				x: box.x * width,
				y: box.y * height,
				width: box.width * width,
				height: box.height * height
			}))}
			{@const isHovered = hoveredCommentId === comment.id}
			{@const isFocused = focusedCommentId === comment.id}
			{@const isActive = isHovered || isFocused}

			<div class="annotation-group pointer-events-none">
				{#each scaledBoxes as box, boxIdx (`${comment.id}-${boxIdx}`)}
					{@const margin = 1}
					<div
						class="absolute rounded-sm transition-all duration-300"
						style:left="{box.x - margin}px"
						style:top="{box.y - margin}px"
						style:width="{box.width + margin * 2}px"
						style:height="{box.height + margin * 2}px"
						style:background-color={annotation.color}
						style:opacity={isActive ? '0.5' : '0.3'}
						style:border={isActive ? `2px solid ${annotation.color}` : 'none'}
						style:box-shadow={isFocused
							? `0 4px 12px rgba(0, 0, 0, 0.15), 0 0 0 3px ${annotation.color}40`
							: isHovered
								? `0 2px 8px rgba(0, 0, 0, 0.1)`
								: 'none'}
						style:box-sizing="border-box"
					></div>
				{/each}
			</div>
		{/each}
	</div>
{/if}
