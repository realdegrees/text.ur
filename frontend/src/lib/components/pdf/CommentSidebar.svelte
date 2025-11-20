<script lang="ts">
	import type { CommentRead } from '$api/types';
	import type { Annotation } from '$types/pdf';
	import { commentStore } from '$lib/stores/commentStore';
	import CommentGroup from './CommentGroup.svelte';
	import { browser } from '$app/environment';
	interface Props {
		comments: CommentRead[];
		pageDataArray: Array<{ pageNumber: number; width: number; height: number }>;
		pdfContainerRef: HTMLDivElement | null;
		scrollContainerRef: HTMLDivElement | null;
		scale: number;
		isDragging: boolean;
		hoveredCommentId?: number | null;
		focusedCommentId?: number | null;
		hoverDelayMs?: number;
	}

	let {
		comments = [],
		pageDataArray = [],
		pdfContainerRef = null,
		scrollContainerRef = null,
		scale = 1,
		isDragging = false,
		hoveredCommentId = $bindable(null),
		focusedCommentId = $bindable(null),
		hoverDelayMs = 200
	}: Props = $props();

	let sidebarRef: HTMLDivElement | null = $state(null);
	let deleteConfirmId = $state<number | null>(null);
	let selectedCommentInGroup = $state<{ [groupId: string]: number }>({});
	let hoveredGroupId = $state<string | null>(null);

	// Store actual line positions calculated from DOM
	interface LinePosition {
		x1: number;
		y1: number;
		x2: number;
		y2: number;
		color: string;
		commentId: number;
	}
	let linePositions = $state<Map<string, LinePosition>>(new Map());

	interface PositionedComment {
		comment: CommentRead;
		annotation: Annotation;
		idealTop: number;
		actualTop: number;
		highlightTop: number;
		highlightBottom: number;
		highlightLeftX: number;
		highlightRightX: number;
	}

	interface CommentGroupData {
		id: string;
		comments: CommentRead[];
		actualTop: number;
		highlightTop: number;
		highlightBottom: number;
		highlightLeftX: number;
		highlightRightX: number;
	}

	const COMMENT_HEIGHT = 80;
	const COMMENT_COLLAPSED_HEIGHT = 32;
	const MIN_GAP = 8;
	const GROUP_THRESHOLD = 40; // Comments within 40px are grouped

	// Get page offset from top of scroll container
	function getPageOffsetTop(pageNumber: number): number {
		if (!scrollContainerRef || !pdfContainerRef) return 0;

		const pageElement = pdfContainerRef.querySelector(`[data-page-number="${pageNumber}"]`);
		if (!pageElement) return 0;

		const scrollRect = scrollContainerRef.getBoundingClientRect();
		const pageRect = pageElement.getBoundingClientRect();

		return pageRect.top - scrollRect.top + scrollContainerRef.scrollTop;
	}

	// Get highlight position
	function getHighlightPosition(annotation: Annotation): {
		leftX: number;
		rightX: number;
		top: number;
		bottom: number;
	} {
		if (!annotation?.boundingBoxes || annotation.boundingBoxes.length === 0) {
			return { leftX: 0, rightX: 0, top: 0, bottom: 0 };
		}

		const pageData = pageDataArray.find((p) => p.pageNumber === annotation.pageNumber);
		if (!pageData || pageData.width === 0 || pageData.height === 0) {
			return { leftX: 0, rightX: 0, top: 0, bottom: 0 };
		}

		if (!pdfContainerRef || !sidebarRef) return { leftX: 0, rightX: 0, top: 0, bottom: 0 };

		// Find the topmost box
		const topBox = annotation.boundingBoxes.reduce((prev, curr) => {
			return curr.y < prev.y ? curr : prev;
		});

		// Find the bottommost box
		const bottomBox = annotation.boundingBoxes.reduce((prev, curr) => {
			const prevBottom = prev.y + prev.height;
			const currBottom = curr.y + curr.height;
			return currBottom > prevBottom ? curr : prev;
		});

		// Find the leftmost box
		const leftBox = annotation.boundingBoxes.reduce((prev, curr) => {
			return curr.x < prev.x ? curr : prev;
		});

		// Find the rightmost box
		const rightBox = annotation.boundingBoxes.reduce((prev, curr) => {
			const prevRight = prev.x + prev.width;
			const currRight = curr.x + curr.width;
			return currRight > prevRight ? curr : prev;
		});

		const pageElement = pdfContainerRef.querySelector(
			`[data-page-number="${annotation.pageNumber}"]`
		);
		if (!pageElement) return { leftX: 0, rightX: 0, top: 0, bottom: 0 };

		const pageOffsetTop = getPageOffsetTop(annotation.pageNumber);

		// Calculate scaled dimensions (these are deterministic, no DOM query race condition)
		const scaledWidth = pageData.width * scale;
		const scaledHeight = pageData.height * scale;

		// Get sidebar position
		const sidebarRect = sidebarRef.getBoundingClientRect();

		// Get PDF container position (parent of all pages)
		const pdfContainerRect = pdfContainerRef.getBoundingClientRect();

		// Calculate page's left position relative to sidebar
		// PDF container has padding (p-4 = 16px on each side)
		const PDF_PADDING = 16;
		const pageLeftRelativeToContainer = PDF_PADDING;
		const pageLeftRelativeSidebar = pdfContainerRect.left - sidebarRect.left + pageLeftRelativeToContainer;

		// Calculate highlight positions within the page (using scaled dimensions)
		const highlightLeftWithinPage = leftBox.x * scaledWidth;
		const highlightRightWithinPage = (rightBox.x + rightBox.width) * scaledWidth;

		// Calculate absolute positions relative to sidebar
		const highlightLeftX = pageLeftRelativeSidebar + highlightLeftWithinPage;
		const highlightRightX = pageLeftRelativeSidebar + highlightRightWithinPage;

		// Calculate vertical positions
		const highlightTop = pageOffsetTop + topBox.y * scaledHeight;
		const highlightBottom = pageOffsetTop + (bottomBox.y + bottomBox.height) * scaledHeight;

		return {
			leftX: highlightLeftX,
			rightX: highlightRightX,
			top: highlightTop,
			bottom: highlightBottom
		};
	}

	// Group comments and calculate positions with collision avoidance
	let commentGroups = $derived.by((): CommentGroupData[] => {
		// Explicitly access scale to ensure reactivity when it changes
		const currentScale = scale;

		if (!pdfContainerRef || !sidebarRef || !scrollContainerRef || pageDataArray.length === 0) {
			return [];
		}

		// First, calculate ideal positions for all comments
		const positioned: PositionedComment[] = [];

		for (const comment of comments) {
			const annotation = comment.annotation as unknown as Annotation;
			if (!annotation?.pageNumber) continue;

			const highlightPos = getHighlightPosition(annotation);

			positioned.push({
				comment,
				annotation,
				idealTop: highlightPos.top,
				actualTop: 0,
				highlightTop: highlightPos.top,
				highlightBottom: highlightPos.bottom,
				highlightLeftX: highlightPos.leftX,
				highlightRightX: highlightPos.rightX
			});
		}

		// Sort by ideal position
		positioned.sort((a, b) => a.idealTop - b.idealTop);

		// Group comments that are close together
		const groups: CommentGroupData[] = [];
		let currentGroup: PositionedComment[] = [];

		for (let i = 0; i < positioned.length; i++) {
			const current = positioned[i];

			if (currentGroup.length === 0) {
				currentGroup.push(current);
			} else {
				const lastInGroup = currentGroup[currentGroup.length - 1];
				// Check if current comment is close enough to group with previous
				if (Math.abs(current.idealTop - lastInGroup.idealTop) <= GROUP_THRESHOLD) {
					currentGroup.push(current);
				} else {
					// Start new group - store all positioned comments for later lookup
					groups.push({
						id: currentGroup.map((c) => c.comment.id).join('-'),
						comments: currentGroup.map((c) => c.comment),
						actualTop: 0,
						highlightTop: 0, // Will be set based on active comment
						highlightBottom: 0, // Will be set based on active comment
						highlightLeftX: 0, // Will be set based on active comment
						highlightRightX: 0 // Will be set based on active comment
					});
					currentGroup = [current];
				}
			}
		}

		// Add last group
		if (currentGroup.length > 0) {
			groups.push({
				id: currentGroup.map((c) => c.comment.id).join('-'),
				comments: currentGroup.map((c) => c.comment),
				actualTop: 0,
				highlightTop: 0, // Will be set based on active comment
				highlightBottom: 0, // Will be set based on active comment
				highlightLeftX: 0, // Will be set based on active comment
				highlightRightX: 0 // Will be set based on active comment
			});
		}

		// Set highlight positions based on active comment in each group
		// This will be recalculated in the template based on hoveredCommentId
		for (const group of groups) {
			// Just set defaults here, actual position determined by active comment in template
			const firstPositioned = positioned.find((p) => p.comment.id === group.comments[0].id);
			if (firstPositioned) {
				group.highlightTop = firstPositioned.highlightTop;
				group.highlightBottom = firstPositioned.highlightBottom;
				group.highlightLeftX = firstPositioned.highlightLeftX;
				group.highlightRightX = firstPositioned.highlightRightX;
			}
		}

		// Store positioned data for later lookup
		groups.forEach((g) => {
			(g as any).positionedData = positioned.filter((p) =>
				g.comments.some((c) => c.id === p.comment.id)
			);
		});

		// Apply collision detection to groups
		for (let i = 0; i < groups.length; i++) {
			const group = groups[i];

			// Calculate ideal top for group (average of all comments in group)
			const avgIdealTop =
				positioned
					.filter((p) => group.comments.some((c) => c.id === p.comment.id))
					.reduce((sum, p) => sum + p.idealTop, 0) / group.comments.length;

			if (i === 0) {
				group.actualTop = Math.max(0, avgIdealTop);
			} else {
				const prev = groups[i - 1];
				const prevIsExpanded =
					prev.comments.some((c) => c.id === hoveredCommentId || c.id === focusedCommentId) ||
					hoveredGroupId === prev.id;
				const prevHeight = prevIsExpanded ? COMMENT_HEIGHT : COMMENT_COLLAPSED_HEIGHT;
				const prevBottom = prev.actualTop + prevHeight + MIN_GAP;
				group.actualTop = Math.max(avgIdealTop, prevBottom);
			}
		}

		return groups;
	});

	// Group interaction handlers
	function handleGroupClick(groupId: string, event: MouseEvent) {
		event.stopPropagation();
		const group = commentGroups.find(({comments}) => comments.find((c) => c.id.toString() === groupId));
		if (!group) return;

		// If no comment is focused in this group, focus the first one
		const focusedInGroup = group.comments.find((c) => c.id === focusedCommentId);
		if (!focusedInGroup) {
			focusedCommentId = group.comments[0].id;
		} else {
			// Toggle off
			focusedCommentId = null;
		}
		deleteConfirmId = null;
	}

	function handleGroupMouseEnter(groupId: string) {
		// Don't expand comments during divider dragging
		if (isDragging) return;

		hoveredGroupId = groupId;
		const group = commentGroups.find(({comments}) => comments.find((c) => c.id.toString() === groupId));
		if (!group) return;

		// Set hovered to first comment in group or selected comment
		const selected = selectedCommentInGroup[groupId];
		hoveredCommentId = selected || group.comments[0].id;
	}

	function handleGroupMouseLeave() {
		hoveredGroupId = null;
		hoveredCommentId = null;
	}

	function handleDeleteClick(commentId: number, event: MouseEvent) {
		event.stopPropagation();
		deleteConfirmId = commentId;
	}

	async function handleDeleteConfirm(commentId: number, event: MouseEvent) {
		event.stopPropagation();
		await commentStore.delete(commentId);
		focusedCommentId = null;
		hoveredCommentId = null;
		deleteConfirmId = null;
	}

	function handleDeleteCancel(event: MouseEvent) {
		event.stopPropagation();
		deleteConfirmId = null;
	}

	// Handle clicks outside comments
	function handleDocumentClick(event: MouseEvent) {
		const target = event.target as HTMLElement;
		const isCommentClick = target.closest('[data-comment-id]');
		const isHighlightClick = target.closest('.annotation-group');

		if (!isCommentClick && !isHighlightClick) {
			focusedCommentId = null;
			deleteConfirmId = null;
		}
	}

	// Calculate line positions from actual DOM elements
	$effect(() => {
		if (!browser || !pdfContainerRef || !sidebarRef) return;

		// Capture refs to avoid null checks in callback
		const pdfContainer = pdfContainerRef;
		const sidebar = sidebarRef;

		// Access reactive dependencies to ensure recalculation
		const currentScale = scale;
		const currentHovered = hoveredCommentId;
		const currentFocused = focusedCommentId;
		const currentGroups = commentGroups;

		// Use requestAnimationFrame to ensure DOM has updated
		requestAnimationFrame(() => {
			const newPositions = new Map<string, LinePosition>();

			for (const group of currentGroups) {
				// Determine active comment
				const activeCommentId =
					(currentHovered && group.comments.some((c) => c.id === currentHovered)
						? currentHovered
						: selectedCommentInGroup[group.id]) || group.comments[0].id;

				const activeComment = group.comments.find((c) => c.id === activeCommentId);
				if (!activeComment) continue;

				const annotation = activeComment.annotation as unknown as Annotation;
				if (!annotation) continue;

				// Check if comment is expanded or hovered
				const isExpanded =
					group.comments.some((c) => c.id === currentFocused || c.id === currentHovered) ||
					hoveredGroupId === group.id;

				if (!isExpanded && !group.comments.some((c) => c.id === currentHovered)) continue;

				// Query annotation group
				const annotationGroup = pdfContainer.querySelector(
					`[data-comment-id="${activeCommentId}"]`
				);
				if (!annotationGroup) continue;

				// Find all highlight boxes within the annotation group
				const highlightBoxes = annotationGroup.querySelectorAll('[data-highlight-box]');
				if (highlightBoxes.length === 0) continue;

				// Find the topmost-leftmost highlight box
				let topmostLeftmostBox: Element | null = null;
				let minTop = Infinity;
				let minLeft = Infinity;

				for (const box of highlightBoxes) {
					const rect = box.getBoundingClientRect();
					if (rect.top < minTop || (rect.top === minTop && rect.left < minLeft)) {
						minTop = rect.top;
						minLeft = rect.left;
						topmostLeftmostBox = box;
					}
				}

				if (!topmostLeftmostBox) continue;

				// Query comment element
				const commentEl = sidebar.querySelector(
					`[data-active-comment="${activeCommentId}"]`
				);
				if (!commentEl) continue;

				// Get bounding rects
				const sidebarRect = sidebar.getBoundingClientRect();
				const highlightRect = (topmostLeftmostBox as Element).getBoundingClientRect();
				const commentRect = commentEl.getBoundingClientRect();

				// Calculate line positions relative to sidebar
				// Anchor to top-left of topmost-leftmost highlight box
				const x1 = highlightRect.left - sidebarRect.left;
				const y1 = highlightRect.top - sidebarRect.top;

				// Anchor to center-center of comment
				const x2 = commentRect.left - sidebarRect.left + commentRect.width / 2;
				const y2 = commentRect.top - sidebarRect.top + commentRect.height / 2;

				newPositions.set(group.id, {
					x1,
					y1,
					x2,
					y2,
					color: annotation.color,
					commentId: activeCommentId
				});
			}

			linePositions = newPositions;
		});
	});

	// Setup global click listener
	$effect(() => {
		if (browser) {
			document.addEventListener('click', handleDocumentClick);
			return () => {
				document.removeEventListener('click', handleDocumentClick);
			};
		}
	});
</script>

<div
	bind:this={sidebarRef}
	class="comment-sidebar relative flex-1 overflow-visible bg-background pr-2"
>
	{#each commentGroups as group (group.id)}
		{@const expanded =
			group.comments.some((c) => c.id === focusedCommentId) ||
			group.comments.some((c) => c.id === hoveredCommentId) ||
			hoveredGroupId === group.id}
		{@const hovered =
			hoveredGroupId === group.id || group.comments.some((c) => c.id === hoveredCommentId)}
		{@const sidebarWidth = sidebarRef?.getBoundingClientRect().width || 0}
		{@const commentLeftEdge = sidebarWidth - 8}

		{@const activeCommentId =
			hoveredCommentId && group.comments.some((c) => c.id === hoveredCommentId)
				? hoveredCommentId
				: selectedCommentInGroup[group.id] || group.comments[0].id}
		{@const activeComment =
			group.comments.find((c) => c.id === activeCommentId) || group.comments[0]}
		{@const activeAnnotation = activeComment.annotation as unknown as Annotation}

		{@const linePos = linePositions.get(group.id)}

		<!-- Connection line (drawn from actual DOM positions) -->
		{#if (expanded || hovered) && linePos}
			<svg
				class="pointer-events-none absolute left-0 top-0 z-10 overflow-visible"
				style:width="{sidebarWidth + 500}px"
				style:height="{Math.max(linePos.y1, linePos.y2) + 50}px"
				style:filter='drop-shadow(0 2px 6px rgba(0, 0, 0, 0.2))'
			>
				<line
					x1={linePos.x1}
					y1={linePos.y1}
					x2={linePos.x2}
					y2={linePos.y2}
					stroke={linePos.color}
					stroke-width='4'
					stroke-opacity='0.9'
				/>
			</svg>
		{/if}

		<!-- Render comment group -->
		<CommentGroup
			comments={group.comments.length > 1 ? group.comments : [group.comments[0]]}
			top={group.actualTop}
			{expanded}
			{hovered}
			selectedCommentId={activeCommentId}
			{deleteConfirmId}
			{hoverDelayMs}
			onClick={(e: MouseEvent) => handleGroupClick(group.id, e)}
			onMouseEnter={() => handleGroupMouseEnter(group.id)}
			onMouseLeave={handleGroupMouseLeave}
			onCommentSelect={(commentId: number) => {
				selectedCommentInGroup[group.id] = commentId;
				hoveredCommentId = commentId;
			}}
			onDeleteClick={handleDeleteClick}
			onDeleteConfirm={handleDeleteConfirm}
			onDeleteCancel={handleDeleteCancel}
		/>
	{/each}
</div>

<style>
	.comment-sidebar {
		min-height: 100%;
		position: relative;
	}

	/* Ensure connection lines can extend beyond sidebar bounds */
	.comment-sidebar :global(svg) {
		overflow: visible;
	}
</style>
