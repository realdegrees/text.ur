<script lang="ts">
	import { documentStore, type CommentState } from '$lib/runes/document.svelte';
	import { hasHoverCapability } from '$lib/util/responsive.svelte';

	interface Props {
		commentState?: CommentState;
		opacity?: number;
		yPosition: number;
		scrollTop?: number;
	}

	// TODO: use position data from cluster instead of recalculating
	let { commentState, opacity = 1, yPosition, scrollTop }: Props = $props();

	interface LineCoordinates {
		startX: number;
		startY: number;
		endX: number;
		endY: number;
	}

	let lineCoords = $derived.by<LineCoordinates | null>(() => {
		void documentStore.documentScale;
		void yPosition;
		void scrollTop;
		void opacity;

		// Find all highlight elements for this comment
		const highlightEls = commentState?.highlightElements;
		const isMobile = !hasHoverCapability();

		// Get the rightmost edge from all highlights for horizontal positioning
		let maxRight = -Infinity;
		let minTop = +Infinity;
		let heightTotal = 0;

		if (!highlightEls || highlightEls.length === 0) {
			return null;
		}

		highlightEls.forEach((el) => {
			const rect = el.getBoundingClientRect();
			heightTotal += rect.height;
			maxRight = Math.max(maxRight, rect.right);
			minTop = Math.min(minTop, rect.top);
		});

		// End point: rightmost edge of all highlights, vertically centered on first highlight
		const HIGHLIGHT_OFFSET = 12; // pixels of gap from highlight edge
		const endX = maxRight + HIGHLIGHT_OFFSET;
		const endY = minTop + heightTotal / 2;

		let startX: number;
		let startY: number;

		if (isMobile) {
			// Mobile: Anchor to the top center of the mobile comment panel
			const mobilePanel = document.querySelector('.mobile-comment-panel');
			if (!mobilePanel) return null;

			const panelRect = mobilePanel.getBoundingClientRect();

			// Anchor to center top of panel
			startX = panelRect.left + panelRect.width / 2;
			startY = panelRect.top;
		} else {
			// Desktop: Anchor to sidebar comment cluster
			const sidebarRect = documentStore.commentSidebarRef?.getBoundingClientRect();
			if (!sidebarRect) return null;

			// Calculate cluster position from data instead of reading DOM
			const LEFT_PADDING = 12; // left-3 class = 0.75rem = 12px
			const clusterLeft = sidebarRect.left + LEFT_PADDING;
			const clusterTop = sidebarRect.top + yPosition;

			// Start point: at cluster (using calculated position from data)
			const COMMENT_OFFSET = -1.5; // pixels of offset from left edge of cluster
			startX = clusterLeft + COMMENT_OFFSET;
			startY = clusterTop + 36; // ~40px from top is where quote area is
		}

		return { startX, startY, endX, endY };
	});

	let lineLength = $derived(
		lineCoords
			? Math.sqrt(
					Math.pow(lineCoords.endX - lineCoords.startX, 2) +
						Math.pow(lineCoords.endY - lineCoords.startY, 2)
				)
			: 0
	);

	let angle = $derived(
		lineCoords
			? Math.atan2(lineCoords.endY - lineCoords.startY, lineCoords.endX - lineCoords.startX)
			: 0
	);
</script>

<div class="pointer-events-none fixed inset-0 overflow-visible">
	{#if lineCoords}
		<svg
			class="absolute inset-0 h-full w-full overflow-visible"
			style="opacity: {opacity}; --line-length: {lineLength}px; --angle: {angle}rad; --start-x: {lineCoords.startX}px; --start-y: {lineCoords.startY}px; --end-x: {lineCoords.endX}px; --end-y: {lineCoords.endY}px;"
		>
			<defs>
				<mask id="end-dot-mask-{commentState?.id}">
					<circle r="8" fill="white" />
					<circle r="3.5" fill="black" />
				</mask>
			</defs>
			<!--Start Circle-->
			<circle cx={lineCoords.startX} cy={lineCoords.startY} r="4" class="start-dot fill-primary" />
			<!-- Main line -->
			<line
				x1={lineCoords.startX}
				y1={lineCoords.startY}
				x2={lineCoords.endX}
				y2={lineCoords.endY}
				stroke="currentColor"
				stroke-width="4"
				class="connection-line text-primary/70"
				stroke-dasharray={lineLength}
				stroke-dashoffset={lineLength}
			/>
			<!-- End dot (at highlight) with inner cutout - travels with line -->
			<g class="end-dot-group" mask="url(#end-dot-mask-{commentState?.id})">
				<circle r="8" class="fill-primary" />
			</g>
		</svg>
	{/if}
</div>

<style>
	.start-dot {
		animation: fadeIn 0.3s ease-out forwards;
	}

	.connection-line {
		animation:
			drawLine 0.5s ease-out forwards,
			fadeLine 0.3s ease-out 0.5s forwards;
	}

	.end-dot-group {
		transform-origin: 0 0;
		animation: travelAlongLine 0.5s ease-out forwards;
	}

	@keyframes fadeIn {
		from {
			opacity: 0;
		}
		to {
			opacity: 1;
		}
	}

	@keyframes drawLine {
		to {
			stroke-dashoffset: 0;
		}
	}

	@keyframes fadeLine {
		to {
			opacity: 0.3;
		}
	}

	@keyframes travelAlongLine {
		from {
			transform: translate(var(--start-x), var(--start-y));
		}
		to {
			transform: translate(var(--end-x), var(--end-y));
		}
	}
</style>
