<script lang="ts">
	import { documentStore, type VisibleLineInfo } from '$lib/runes/document.svelte';
	import { hasHoverCapability } from '$lib/util/responsive.svelte';
	import { onMount } from 'svelte';
	import {
		LINE_CORNER_RADIUS,
		LINE_STROKE_WIDTH,
		LINE_HOVERED_STROKE_WIDTH,
		LINE_ENDPOINT_RADIUS,
		LINE_FADE_MS,
		LINE_OPACITY,
		LINE_CHANNEL_GAP
	} from './constants';

	interface Props {
		scrollTop: number;
	}

	let { scrollTop }: Props = $props();

	/**
	 * Build an orthogonal SVG path with rounded corners at the two bends.
	 *
	 * Route: comment(startX,startY) --H left--> channelX --V--> endY --H left--> highlight(endX,endY)
	 */
	function buildOrthogonalPath(
		startX: number,
		startY: number,
		channelX: number,
		endX: number,
		endY: number,
		r: number
	): string {
		const dy = endY - startY;
		const absDy = Math.abs(dy);

		if (absDy < 1) {
			return `M ${startX} ${startY} H ${endX}`;
		}

		const hGap1 = Math.abs(startX - channelX);
		const hGap2 = Math.abs(channelX - endX);
		const actualR = Math.min(r, absDy / 2, hGap1 / 2, hGap2 / 2);

		if (actualR < 1) {
			return `M ${startX} ${startY} H ${channelX} V ${endY} H ${endX}`;
		}

		if (dy > 0) {
			return [
				`M ${startX} ${startY}`,
				`H ${channelX + actualR}`,
				`A ${actualR} ${actualR} 0 0 0 ${channelX} ${startY + actualR}`,
				`V ${endY - actualR}`,
				`A ${actualR} ${actualR} 0 0 1 ${channelX - actualR} ${endY}`,
				`H ${endX}`
			].join(' ');
		} else {
			return [
				`M ${startX} ${startY}`,
				`H ${channelX + actualR}`,
				`A ${actualR} ${actualR} 0 0 1 ${channelX} ${startY - actualR}`,
				`V ${endY + actualR}`,
				`A ${actualR} ${actualR} 0 0 0 ${channelX - actualR} ${endY}`,
				`H ${endX}`
			].join(' ');
		}
	}

	/**
	 * Get valid highlight rects for a comment, filtering detached/zero-size.
	 */
	function getValidHighlightRects(info: VisibleLineInfo): DOMRect[] {
		const els = info.commentState.highlightElements;
		if (!els || els.length === 0) return [];

		const rects: DOMRect[] = [];
		for (const el of els) {
			if (!el.isConnected) continue;
			const rect = el.getBoundingClientRect();
			if (rect.width === 0 && rect.height === 0) continue;
			rects.push(rect);
		}
		return rects;
	}

	// --- SVG element ref for imperative DOM updates ---
	let svgRef: SVGSVGElement | null = $state(null);

	/**
	 * Imperatively update SVG content from live DOM positions.
	 * Completely bypasses Svelte's reactivity for scroll tracking.
	 */
	function updateLines() {
		if (!svgRef) return;

		const isMobile = !hasHoverCapability();
		const pdfRight = documentStore.scrollContainerRef?.getBoundingClientRect().right ?? 0;

		// Single channel X — all vertical segments share this X position
		const channelX = pdfRight + LINE_CHANNEL_GAP;

		// Build SVG content imperatively
		let svgContent = '';

		for (const [id, info] of documentStore.visibleLines) {
			const rects = getValidHighlightRects(info);
			if (rects.length === 0) continue;

			// Highlight bounding box: find the extents of all highlight elements
			let minTop = Infinity;
			let minLeft = Infinity;
			let maxBottom = -Infinity;
			for (const rect of rects) {
				if (rect.top < minTop) minTop = rect.top;
				if (rect.left < minLeft) minLeft = rect.left;
				if (rect.bottom > maxBottom) maxBottom = rect.bottom;
			}
			// Line endpoint anchors at the top-left of the bounding box
			const endX = minLeft;
			const endY = minTop;

			// Comment cluster anchor: top-left corner
			let startX: number;
			let startY: number;

			if (isMobile) {
				const mobilePanel = document.querySelector('.mobile-comment-panel');
				if (!mobilePanel) continue;
				const panelRect = mobilePanel.getBoundingClientRect();
				startX = panelRect.left + panelRect.width / 2;
				startY = panelRect.top;
			} else {
				const clusterEl = info.clusterElement;
				if (!clusterEl || !clusterEl.isConnected) continue;
				const clusterRect = clusterEl.getBoundingClientRect();
				startX = clusterRect.left;
				startY = clusterRect.top;
			}

			const strokeW = info.isHovered ? LINE_HOVERED_STROKE_WIDTH : LINE_STROKE_WIDTH;
			const dotR = info.isHovered ? LINE_ENDPOINT_RADIUS + 1 : LINE_ENDPOINT_RADIUS;
			const color = info.color;

			const pathD = buildOrthogonalPath(startX, startY, channelX, endX, endY, LINE_CORNER_RADIUS);

			svgContent += `<g data-line-id="${id}" style="opacity: ${LINE_OPACITY}; transition: stroke-width ${LINE_FADE_MS}ms ease;">`;
			svgContent += `<circle cx="${startX}" cy="${startY}" r="${dotR}" fill="${color}" />`;
			svgContent += `<path d="${pathD}" fill="none" stroke="${color}" stroke-width="${strokeW}" />`;
			// 4th segment: vertical line down the left edge of the highlight group
			svgContent += `<line x1="${endX}" y1="${minTop}" x2="${endX}" y2="${maxBottom}" stroke="${color}" stroke-width="${strokeW}" />`;
			svgContent += `</g>`;
		}

		// eslint-disable-next-line svelte/no-dom-manipulating -- Intentional imperative rendering to bypass Svelte reactivity batching for scroll performance
		svgRef.innerHTML = svgContent;
	}

	// --- Scroll tracking via direct scroll event + RAF ---
	let rafId: number | null = null;

	function scheduleUpdate() {
		if (rafId !== null) return;
		rafId = requestAnimationFrame(() => {
			rafId = null;
			updateLines();
		});
	}

	onMount(() => {
		const scrollContainer = documentStore.scrollContainerRef;
		if (scrollContainer) {
			scrollContainer.addEventListener('scroll', scheduleUpdate, { passive: true });
		}

		// Initial render
		updateLines();

		return () => {
			if (scrollContainer) {
				scrollContainer.removeEventListener('scroll', scheduleUpdate);
			}
			if (rafId !== null) {
				cancelAnimationFrame(rafId);
			}
		};
	});

	// Re-render when lines are added/removed, hover state changes, or zoom changes.
	// This is the only reactive path — scroll is handled imperatively above.
	$effect(() => {
		void scrollTop;
		void documentStore.documentScale;
		void documentStore.visibleLines.size;
		// Also re-render when any line's hover state might have changed
		for (const [, info] of documentStore.visibleLines) {
			void info.isHovered;
		}
		updateLines();
	});
</script>

<div class="pointer-events-none fixed inset-0 z-30">
	<svg bind:this={svgRef} class="absolute inset-0 h-full w-full overflow-visible"></svg>
</div>
