<script lang="ts">
	import { documentStore, type TypedComment } from '$lib/runes/document.svelte';

	interface Props {
		comment: TypedComment | null;
		opacity?: number;
		yPosition: number;
		scrollTop?: number;
	}

	let { comment, opacity = 1, yPosition, scrollTop }: Props = $props();

	interface LineCoordinates {
		startX: number;
		startY: number;
		endX: number;
		endY: number;
	}



	const calculateLineCoordinates = (): LineCoordinates | null => {
		// Find all highlight elements for this comment
		const state = documentStore.comments.getState(comment?.id ?? -1);
		const highlightEls = state?.highlightElements;
		const sidebarRect = documentStore.commentSidebarRef?.getBoundingClientRect();

		if (!highlightEls || highlightEls.length === 0 || !sidebarRect) {
			console.log('aaaa');

			return null;
		}

		// Get the first highlight for vertical positioning
		const firstHighlightRect = highlightEls[0].getBoundingClientRect();

		// Calculate cluster position from data instead of reading DOM
		const LEFT_PADDING = 12; // left-3 class = 0.75rem = 12px
		const clusterLeft = sidebarRect.left + LEFT_PADDING;
		const clusterTop = sidebarRect.top + yPosition;

		// Get the rightmost edge from all highlights for horizontal positioning
		let maxRight = -Infinity;
		highlightEls.forEach((el) => {
			const rect = el.getBoundingClientRect();
			maxRight = Math.max(maxRight, rect.right);
		});

		// End point: rightmost edge of all highlights, vertically centered on first highlight
		const HIGHLIGHT_OFFSET = 12; // pixels of gap from highlight edge
		const endX = maxRight + HIGHLIGHT_OFFSET;
		const endY = firstHighlightRect.top + firstHighlightRect.height / 2;

		// Start point: at cluster (using calculated position from data)
		const COMMENT_OFFSET = -1.5; // pixels of offset from left edge of cluster
		const startX = clusterLeft + COMMENT_OFFSET;
		const startY = clusterTop + 36; // ~40px from top is where quote area is

		console.log(`Line from (${startX}, ${startY}) to (${endX}, ${endY})`);

		return { startX, startY, endX, endY };
	};

	let lineCoords = $derived.by<LineCoordinates | null>(() => {
		void documentStore.documentScale;
		void documentStore.loadedDocument;
		void yPosition;
		void scrollTop;
		// void comment;
		void opacity;

		return calculateLineCoordinates();
	});
</script>

<div class="pointer-events-none fixed inset-0 overflow-visible">
	{#if lineCoords}
		<svg class="absolute inset-0 h-full w-full overflow-visible" style="opacity: {opacity}">
			<!--Start Circle-->
			<circle cx={lineCoords.startX} cy={lineCoords.startY} r="4" class="fill-primary" />
			<!-- Main line -->
			<line
				x1={lineCoords.startX}
				y1={lineCoords.startY}
				x2={lineCoords.endX}
				y2={lineCoords.endY}
				stroke="currentColor"
				stroke-width="5"
				class="text-primary/70"
			/>
			<!-- End dot (at highlight) -->
			<circle cx={lineCoords.endX} cy={lineCoords.endY} r="8" class="fill-primary" />

			<!-- End dot inner (at highlight) -->
			<circle cx={lineCoords.endX} cy={lineCoords.endY} r="3.5" class="fill-text" />
			<circle cx={lineCoords.endX} cy={lineCoords.endY} r="3.5" class="fill-text" />
		</svg>
	{/if}
</div>
