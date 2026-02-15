<script lang="ts">
	import { documentStore, type CommentState } from '$lib/runes/document.svelte';
	import { hasHoverCapability } from '$lib/util/responsive.svelte';
	import { onMount } from 'svelte';
	import {
		LINE_CORNER_RADIUS,
		LINE_STROKE_WIDTH,
		LINE_HOVERED_STROKE_WIDTH,
		LINE_ENDPOINT_RADIUS,
		LINE_FADE_MS,
		LINE_OPACITY,
		LINE_CHANNEL_GAP,
		DEFAULT_HIGHLIGHT_COLOR
	} from './constants';

	interface Props {
		scrollTop: number;
	}

	let { scrollTop }: Props = $props();

	/**
	 * Build an orthogonal SVG path with rounded corners at the two bends.
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
	 * Get valid highlight rects for a comment state.
	 */
	function getValidHighlightRects(state: CommentState): DOMRect[] {
		const els = state.highlightElements;
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

	interface LineData {
		commentId: number;
		state: CommentState;
		isHovered: boolean;
		color: string;
	}

	/**
	 * Derive which comments should have visible connection lines.
	 * Purely reactive — a line shows when isCommentHovered || isHighlightHovered || longPress.
	 */
	let activeLines: LineData[] = $derived.by(() => {
		const lines: LineData[] = [];
		const longPressId = documentStore.longPressCommentId;

		for (const comment of documentStore.comments.topLevelComments) {
			const state = documentStore.comments.getState(comment.id);
			if (!state) continue;

			const isHovered = !!state.isCommentHovered || !!state.isHighlightHovered;
			const isLongPressed = comment.id === longPressId;

			if (!isHovered && !isLongPressed) continue;

			const color =
				comment.tags && comment.tags.length > 0 ? comment.tags[0].color : DEFAULT_HIGHLIGHT_COLOR;

			lines.push({ commentId: comment.id, state, isHovered, color });
		}

		return lines;
	});

	/**
	 * Compute SVG geometry for each active line.
	 * Depends on scroll/zoom (via scrollTick) and activeLines (reactive).
	 */
	interface RenderedLine {
		id: number;
		color: string;
		strokeW: number;
		dotR: number;
		startX: number;
		startY: number;
		pathD: string;
		minTop: number;
		maxBottom: number;
		endX: number;
	}

	// Bumped every scroll/resize frame to force re-derive of positions
	let scrollTick = $state(0);

	let renderedLines: RenderedLine[] = $derived.by(() => {
		// Subscribe to scroll/zoom
		void scrollTick;
		void scrollTop;
		void documentStore.documentScale;

		const isMobile = !hasHoverCapability();
		const pdfRight = documentStore.scrollContainerRef?.getBoundingClientRect().right ?? 0;
		const channelX = pdfRight + LINE_CHANNEL_GAP;

		const result: RenderedLine[] = [];

		for (const line of activeLines) {
			const rects = getValidHighlightRects(line.state);
			if (rects.length === 0) continue;

			let minTop = Infinity;
			let minLeft = Infinity;
			let maxBottom = -Infinity;
			for (const rect of rects) {
				if (rect.top < minTop) minTop = rect.top;
				if (rect.left < minLeft) minLeft = rect.left;
				if (rect.bottom > maxBottom) maxBottom = rect.bottom;
			}
			const endX = minLeft;
			const endY = minTop;

			let startX: number;
			let startY: number;

			if (isMobile) {
				const mobilePanel = document.querySelector('.mobile-comment-panel');
				if (!mobilePanel) continue;
				const panelRect = mobilePanel.getBoundingClientRect();
				startX = panelRect.left + panelRect.width / 2;
				startY = panelRect.top;
			} else {
				const clusterEl = documentStore.clusterElements.get(line.commentId);
				if (!clusterEl || !clusterEl.isConnected) continue;
				const clusterRect = clusterEl.getBoundingClientRect();
				startX = clusterRect.left;
				startY = clusterRect.top;
			}

			const strokeW = line.isHovered ? LINE_HOVERED_STROKE_WIDTH : LINE_STROKE_WIDTH;
			const dotR = line.isHovered ? LINE_ENDPOINT_RADIUS + 1 : LINE_ENDPOINT_RADIUS;

			const pathD = buildOrthogonalPath(startX, startY, channelX, endX, endY, LINE_CORNER_RADIUS);

			result.push({
				id: line.commentId,
				color: line.color,
				strokeW,
				dotR,
				startX,
				startY,
				pathD,
				minTop,
				maxBottom,
				endX
			});
		}

		return result;
	});

	// Scroll tracking: bump scrollTick so renderedLines re-derives positions
	onMount(() => {
		const scrollContainer = documentStore.scrollContainerRef;
		let rafId: number | null = null;

		function scheduleUpdate() {
			if (rafId !== null) return;
			rafId = requestAnimationFrame(() => {
				rafId = null;
				scrollTick++;
			});
		}

		if (scrollContainer) {
			scrollContainer.addEventListener('scroll', scheduleUpdate, { passive: true });
		}

		return () => {
			if (scrollContainer) {
				scrollContainer.removeEventListener('scroll', scheduleUpdate);
			}
			if (rafId !== null) {
				cancelAnimationFrame(rafId);
			}
		};
	});
</script>

<div class="pointer-events-none fixed inset-0 z-30">
	<svg class="absolute inset-0 h-full w-full overflow-visible">
		{#each renderedLines as line (line.id)}
			<g
				style="opacity: {LINE_OPACITY}; transition: opacity {LINE_FADE_MS}ms ease, stroke-width {LINE_FADE_MS}ms ease;"
			>
				<circle cx={line.startX} cy={line.startY} r={line.dotR} fill={line.color} />
				<path d={line.pathD} fill="none" stroke={line.color} stroke-width={line.strokeW} />
				<line
					x1={line.endX}
					y1={line.minTop}
					x2={line.endX}
					y2={line.maxBottom}
					stroke={line.color}
					stroke-width={line.strokeW}
				/>
			</g>
		{/each}
	</svg>
</div>
