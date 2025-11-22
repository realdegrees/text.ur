<script lang="ts">
	import { documentStore } from '$lib/runes/document.svelte.js';

	interface Props {
		pdfContainer: HTMLDivElement | null;
		sidebarContainer: HTMLDivElement | null;
	}

	let { pdfContainer, sidebarContainer }: Props = $props();

	// Get the active comment to draw line for
	let selectedComment = $derived(documentStore.selectedComment);
	let hoveredComment = $derived(documentStore.hoveredComment);
	let pinnedComment = $derived(documentStore.pinnedComment);

	// Determine which comment to draw the line for
	// Priority: pinned > selected > hovered
	let activeComment = $derived(
		pinnedComment ?? selectedComment ?? hoveredComment
	);

	let activeCommentId = $derived(activeComment?.id ?? null);

	// Line coordinates (viewport-relative, then converted to container-relative)
	let lineCoords = $state<{
		startX: number;
		startY: number;
		endX: number;
		endY: number;
	} | null>(null);

	// Track the parent container for relative positioning
	let parentContainer: HTMLElement | null = $state(null);

	const calculateLineCoordinates = () => {
		if (!activeCommentId || !pdfContainer || !sidebarContainer || !parentContainer) {
			lineCoords = null;
			return;
		}

		// Find all highlight elements for this comment
		const highlightEls = pdfContainer.querySelectorAll(
			`.annotation-highlight[data-comment-id="${activeCommentId}"]`
		);

		// Find the badge element in the sidebar
		const badgeEl = sidebarContainer.querySelector(
			`[data-comment-badge="${activeCommentId}"]`
		) as HTMLElement | null;

		if (highlightEls.length === 0 || !badgeEl) {
			lineCoords = null;
			return;
		}

		const parentRect = parentContainer.getBoundingClientRect();
		const badgeRect = badgeEl.getBoundingClientRect();

		// Get the first highlight for vertical positioning
		const firstHighlightRect = highlightEls[0].getBoundingClientRect();

		// Get the rightmost edge from all highlights for horizontal positioning
		let maxRight = -Infinity;
		highlightEls.forEach((el) => {
			const rect = el.getBoundingClientRect();
			maxRight = Math.max(maxRight, rect.right);
		});

		// End point: rightmost edge of all highlights, vertically centered on first highlight
		const HIGHLIGHT_OFFSET = 6; // pixels of gap from highlight edge
		const endX = maxRight - parentRect.left + HIGHLIGHT_OFFSET;
		const endY = firstHighlightRect.top + firstHighlightRect.height / 2 - parentRect.top;

		// Start point: left edge of badge, near the top (where annotation quote is)
		const startX = badgeRect.left - parentRect.left;
		const startY = badgeRect.top + 40 - parentRect.top; // ~40px from top is where quote area is

		lineCoords = { startX, startY, endX, endY };
	};

	// Recalculate on relevant changes
	$effect(() => {
		// Dependencies
		void activeCommentId;

		// Calculate after a short delay to allow DOM to update
		const timeout = setTimeout(calculateLineCoordinates, 10);
		return () => clearTimeout(timeout);
	});

	// Also recalculate on scroll
	$effect(() => {
		if (!pdfContainer) return;

		const handleScroll = () => {
			if (activeCommentId) {
				requestAnimationFrame(calculateLineCoordinates);
			}
		};

		pdfContainer.addEventListener('scroll', handleScroll);
		return () => pdfContainer.removeEventListener('scroll', handleScroll);
	});

	// Set up a MutationObserver to detect when badges are rendered
	$effect(() => {
		if (!sidebarContainer) return;

		const observer = new MutationObserver(() => {
			if (activeCommentId) {
				requestAnimationFrame(calculateLineCoordinates);
			}
		});

		observer.observe(sidebarContainer, {
			childList: true,
			subtree: true,
			attributes: true,
			attributeFilter: ['data-badge-active']
		});

		return () => observer.disconnect();
	});
</script>

<div
	class="pointer-events-none absolute inset-0 z-40 overflow-visible"
	bind:this={parentContainer}
>
	{#if lineCoords}
		<svg class="absolute inset-0 h-full w-full overflow-visible">
			<!-- Main line -->
			<line
				x1={lineCoords.startX}
				y1={lineCoords.startY}
				x2={lineCoords.endX}
				y2={lineCoords.endY}
				stroke="currentColor"
				stroke-width="2"
				stroke-dasharray="4 2"
				class="text-primary/60"
			/>
			<!-- Start dot (at badge) -->
			<circle
				cx={lineCoords.startX}
				cy={lineCoords.startY}
				r="4"
				class="fill-primary/80"
			/>
			<!-- End dot (at highlight) -->
			<circle
				cx={lineCoords.endX}
				cy={lineCoords.endY}
				r="4"
				class="fill-primary/80"
			/>
		</svg>
	{/if}
</div>
