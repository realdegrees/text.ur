<script lang="ts">
	import { commentStore } from '$lib/stores/commentStore';

	/**
	 * Renders a connection line from a highlight to its comment card.
	 * Simple implementation with CSS-based drawing animation.
	 */

	interface Props {
		activeCommentId?: number | null;
		sidebarRef?: HTMLDivElement | null;
		groupRef?: HTMLElement | null;
		cssScaleFactor?: number;
		visible?: boolean;
		color?: string;
	}

	let {
		activeCommentId = null,
		sidebarRef = null,
		groupRef = null,
		visible = false,
		color = '#000',
		cssScaleFactor = 1
	}: Props = $props();

	const COMMENT_ANCHOR_Y_OFFSET = 5;

	interface LineCoordinates {
		x1: number;
		y1: number;
		x2: number;
		y2: number;
	}

	// Compute line coordinates from highlight to comment
	function computeLineCoordinates(): LineCoordinates | null {
		if (!activeCommentId || !sidebarRef || !groupRef) {
			return null;
		}

		const local = commentStore.getLocalComment(activeCommentId);
		if (!local?.screenPosition) {
			return null;
		}

		const sidebarRect = sidebarRef.getBoundingClientRect();
		const groupRect = groupRef.getBoundingClientRect();

		// Highlight end (right edge)
		const highlightPos = local.screenPosition.highlight;
		const x1 = highlightPos.rightX;
		const y1 = highlightPos.top;

		// Comment end (left edge)
		const x2 = groupRect.left - sidebarRect.left;
		const y2 = groupRect.top - sidebarRect.top + COMMENT_ANCHOR_Y_OFFSET;

		return { x1, y1, x2, y2 };
	}

	// Reactive line coordinates
	let coords = $state<LineCoordinates | null>(null);

	// Update coordinates when dependencies change
	$effect(() => {
		void activeCommentId;
		void cssScaleFactor;
		void visible;

		coords = computeLineCoordinates();
	});

	// SVG viewBox dimensions
	let svgBox = $derived.by(() => {
		if (!coords) {
			return { left: 0, top: 0, width: 100, height: 100 };
		}

		const padding = 10;
		const minX = Math.min(coords.x1, coords.x2) - padding;
		const maxX = Math.max(coords.x1, coords.x2) + padding;
		const minY = Math.min(coords.y1, coords.y2) - padding;
		const maxY = Math.max(coords.y1, coords.y2) + padding;

		return {
			left: minX,
			top: minY,
			width: maxX - minX,
			height: maxY - minY
		};
	});

	// Path coordinates relative to SVG viewport
	let pathCoords = $derived.by(() => {
		if (!coords) return null;

		return {
			x1: coords.x1 - svgBox.left,
			y1: coords.y1 - svgBox.top,
			x2: coords.x2 - svgBox.left,
			y2: coords.y2 - svgBox.top
		};
	});

	// SVG path string
	let pathD = $derived(
		pathCoords ? `M ${pathCoords.x2} ${pathCoords.y2} L ${pathCoords.x1} ${pathCoords.y1}` : ''
	);

	// Path length for stroke-dasharray animation
	let pathLength = $derived.by(() => {
		if (!pathCoords) return 0;
		const dx = pathCoords.x1 - pathCoords.x2;
		const dy = pathCoords.y1 - pathCoords.y2;
		return Math.sqrt(dx * dx + dy * dy);
	});

	// Only render when we have valid coordinates and visibility
	let shouldRender = $derived(coords !== null && visible);
</script>

{#if shouldRender}
	<svg
		class="connection-svg"
		style:left="{svgBox.left}px"
		style:top="{svgBox.top}px"
		style:width="{svgBox.width}px"
		style:height="{svgBox.height}px"
	>
		<path
			class="connection-path"
			d={pathD}
			stroke={color}
			stroke-dasharray={pathLength}
			stroke-dashoffset={pathLength}
		/>
	</svg>
{/if}

<style>
	.connection-svg {
		position: absolute;
		pointer-events: none;
		overflow: hidden;
		z-index: 30;
	}

	.connection-path {
		fill: none;
		stroke-width: 4;
		stroke-linecap: round;
		stroke-linejoin: round;
		filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.15));
		animation: draw-line 250ms ease-out forwards;
	}

	@keyframes draw-line {
		to {
			stroke-dashoffset: 0;
		}
	}
</style>
