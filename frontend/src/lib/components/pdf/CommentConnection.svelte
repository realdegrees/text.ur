<script lang="ts">
	import { draw } from 'svelte/transition';

	/**
	 * Component that renders a straight SVG connection between a sidebar comment group
	 * and its corresponding annotation highlight in the PDF container.
	 */
	// No lifecycle hooks are needed since no timers or animation side-effects are used.

	interface Props {
		commentIds?: number[];
		activeCommentId?: number | null;
		pdfContainerRef?: HTMLDivElement | null;
		sidebarRef?: HTMLDivElement | null;
		visible?: boolean;
		color?: string;
	}

	let {
		commentIds = [],
		activeCommentId = null,
		pdfContainerRef = null,
		sidebarRef = null,
		visible = false,
		color = '#000',
	}: Props = $props();

	const COMMENT_ANCHOR_Y_OFFSET = 5;

	// Path state
	let pathD = $state('');

	// Computed layout values
	let sidebarWidth = $state(0);

	interface LinePosition {
		x1: number;
		y1: number;
		x2: number;
		y2: number;
		color: string;
		commentId: number;
	}

	let linePos = $state<LinePosition | null>(null);

	// Cleanup on destroy

	// Compute `pathD` from DOM; animation handled by Svelte `draw` transition
	$effect(() => {
		// Compute sidebar width for sizing
		try {
			sidebarWidth = sidebarRef?.getBoundingClientRect().width || 0;
		} catch {
			sidebarWidth = 0;
		}

		// If required things are missing or not visible, clear
		if (!pdfContainerRef || !sidebarRef || !visible || !activeCommentId) {
			pathD = '';
			linePos = null;
			return;
		}

		// Otherwise compute anchors from DOM
		requestAnimationFrame(() => {
			const annotationGroup = pdfContainerRef!.querySelector(
				`[data-comment-id="${activeCommentId}"]`
			) as Element | null;

			const groupSelector = commentIds.join('-');
			const commentEl = sidebarRef!.querySelector(
				`[data-comment-group="${groupSelector}"]`
			) as Element | null;

			if (!annotationGroup || !commentEl) {
				linePos = null;
				pathD = '';
				return;
			}

			const highlightBox = annotationGroup.querySelector('[data-highlight-box]') as Element | null;
			if (!highlightBox) {
				linePos = null;
				pathD = '';
				return;
			}

			const aRect = highlightBox.getBoundingClientRect();
			const cRect = commentEl.getBoundingClientRect();
			const sidebarRect = sidebarRef!.getBoundingClientRect();

			// Anchor A: top-right of the annotation highlight box
			const x1 = aRect.right - sidebarRect.left;
			const y1 = aRect.top - sidebarRect.top;

			// Anchor C: left of the comment group element with a small fixed offset
			const x2 = cRect.left - sidebarRect.left;
			const y2 = cRect.top - sidebarRect.top + COMMENT_ANCHOR_Y_OFFSET;

			linePos = { x1, y1, x2, y2, color: color || '#000', commentId: activeCommentId };

			// Straight line between the two anchors.
			const newD = `M ${x2} ${y2} L ${x1} ${y1}`;

			// Update pathD immediately; this will make the connection visible without
			// any animated drawing or transitions.
			pathD = newD;
		});
	});
</script>

{#if linePos && pathD && visible}
	<svg
		class="pointer-events-none absolute left-0 top-0 z-30 overflow-visible"
		style:width="{Math.max(
			sidebarWidth + 500,
			linePos ? Math.abs(linePos.x2 - linePos.x1) + 50 : 300
		)}px"
		style:height="{Math.max(linePos ? Math.max(linePos.y1, linePos.y2) + 50 : 150, 50)}px"
		style:filter="drop-shadow(0 2px 6px rgba(0, 0, 0, 0.2))"
	>
		<path
			d={pathD}
			class="rounded"
			fill="none"
			stroke={linePos?.color ?? '#000'}
			stroke-width="4"
			stroke-linecap="round"
			in:draw={{ duration: 300 }}
			out:draw={{ duration: 300 }}
		/>
	</svg>
{/if}

<style>
	:global(.comment-sidebar) :global(svg) {
		overflow: visible;
	}
</style>
