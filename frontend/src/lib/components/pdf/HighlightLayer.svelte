<script lang="ts">
	import type { CommentRead } from '$api/types';
	import type { Annotation } from '$types/pdf';

	let {
		comments = [],
		currentPage,
		textLayerWidth,
		textLayerHeight,
		hoveredCommentId,
		focusedCommentId
	}: {
		comments: CommentRead[];
		currentPage: number;
		textLayerWidth: number;
		textLayerHeight: number;
		hoveredCommentId: number | null;
		focusedCommentId: number | null;
	} = $props();

	// Filter comments for current page
	let currentPageComments = $derived(
		comments.filter(({ annotation }) => annotation?.pageNumber === currentPage)
	);
</script>

{#if textLayerWidth > 0 && textLayerHeight > 0}
	<div class="annotations-layer pointer-events-none absolute left-0 top-0 h-full w-full">
		{#each currentPageComments as comment (comment.id)}
			{@const annotation = comment.annotation as unknown as Annotation}
			{@const scaledBoxes = annotation.boundingBoxes.map((box) => ({
				x: box.x * textLayerWidth,
				y: box.y * textLayerHeight,
				width: box.width * textLayerWidth,
				height: box.height * textLayerHeight
			}))}
			{@const isHovered = hoveredCommentId === comment.id}
			{@const isFocused = focusedCommentId === comment.id}
			{@const isActive = isHovered || isFocused}
			<div class="annotation-group pointer-events-none">
				{#each scaledBoxes as box, boxIdx (`${comment.id}-${boxIdx}`)}
					{@const margin = 0.8}
					<div
						class="absolute rounded-sm transition-all duration-200"
						class:border-2={isActive}
						style:left="{box.x - margin}px"
						style:top="{box.y - margin}px"
						style:width="{box.width + margin * 2}px"
						style:height="{box.height + margin * 2}px"
						style:background-color={annotation.color}
						style:opacity={isActive ? '0.4' : '0.25'}
						style:border-color={isActive ? annotation.color : 'transparent'}
					></div>
				{/each}
			</div>
		{/each}
	</div>
{/if}
