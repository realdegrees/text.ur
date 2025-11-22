import type { Annotation } from '$types/pdf';
import type { LocalComment, CommentGroup } from '$lib/stores/commentStore';

/**
 * Pure utility functions for converting annotation bounding boxes and positions
 * into screen-space coordinates. All functions are deterministic and don't access DOM.
 */

/**
 * Convert annotation normalized bounding boxes (0-1) into pixel-scaled boxes
 * given the page width/height and a scale multiplier.
 */
export function computeScaledBoundingBoxes(
	annotation: Annotation,
	pageData: { pageNumber: number; width: number; height: number },
	scale: number
): Array<{ x: number; y: number; width: number; height: number }> {
	return (annotation.boundingBoxes || []).map((b) => ({
		x: b.x * pageData.width * scale,
		y: b.y * pageData.height * scale,
		width: b.width * pageData.width * scale,
		height: b.height * pageData.height * scale
	}));
}

/**
 * Compute screen-space rectangle for annotation given scaled boxes and DOM
 * element geometry. All rects are expected to be DOMRect-like.
 *
 * DEPRECATED: Use computeHighlightScreenPosition instead for new code.
 * Kept for backwards compatibility.
 */
export function computeScreenRectFromScaledBoxes(
	scaledBoxes: Array<{ x: number; y: number; width: number; height: number }>,
	pageRect: DOMRect,
	pdfContainerRect: DOMRect,
	sidebarRect: DOMRect,
	scrollRect: DOMRect,
	scrollTop: number,
	pdfPadding: number = 16
): { leftX: number; rightX: number; top: number; bottom: number } {
	const topBox = scaledBoxes.reduce((prev, cur) => (cur.y < prev.y ? cur : prev));
	const bottomBox = scaledBoxes.reduce(
		(prev, cur) => (cur.y + cur.height > prev.y + prev.height ? cur : prev)
	);
	const leftBox = scaledBoxes.reduce((prev, cur) => (cur.x < prev.x ? cur : prev));
	const rightBox = scaledBoxes.reduce(
		(prev, cur) => (cur.x + cur.width > prev.x + prev.width ? cur : prev)
	);

	const pageOffsetTop = pageRect.top - scrollRect.top + scrollTop;
	const pageLeftRelativeToContainer = pdfPadding;
	const pageLeftRelativeSidebar =
		pdfContainerRect.left - sidebarRect.left + pageLeftRelativeToContainer;

	const leftX = pageLeftRelativeSidebar + leftBox.x;
	const rightX = pageLeftRelativeSidebar + rightBox.x + rightBox.width;
	const top = pageOffsetTop + topBox.y;
	const bottom = pageOffsetTop + bottomBox.y + bottomBox.height;

	return { leftX, rightX, top, bottom };
}

/**
 * Compute highlight screen position relative to sidebar coordinate system.
 * Prefers using registered highlight element when available (follows CSS transforms),
 * otherwise computes from annotation data.
 */
export function computeHighlightScreenPosition(options: {
	annotation: Annotation;
	pageData: { pageNumber: number; width: number; height: number };
	scale: number;
	pageElement: HTMLElement | null;
	highlightElement: HTMLElement | null;
	pdfContainerRef: HTMLElement | null;
	scrollContainerRef: HTMLElement | null;
	sidebarRef: HTMLElement | null;
	scaledBoxes: Array<{ x: number; y: number; width: number; height: number }>;
}): { leftX: number; rightX: number; top: number; bottom: number } | null {
	const {
		annotation,
		pageData,
		scale,
		pageElement,
		highlightElement,
		pdfContainerRef,
		scrollContainerRef,
		sidebarRef,
		scaledBoxes
	} = options;

	if (!sidebarRef || !pdfContainerRef || !scrollContainerRef) {
		return null;
	}

	const sidebarRect = sidebarRef.getBoundingClientRect();
	const scrollRect = scrollContainerRef.getBoundingClientRect();
	const scrollTop = scrollContainerRef.scrollTop;

	// Prefer using highlight element if available (follows CSS transforms)
	if (highlightElement) {
		const aRect = highlightElement.getBoundingClientRect();
		const leftX = aRect.left - sidebarRect.left;
		const rightX = aRect.right - sidebarRect.left;
		const top = aRect.top - scrollRect.top + scrollTop;
		const bottom = aRect.bottom - scrollRect.top + scrollTop;
		return { leftX, rightX, top, bottom };
	}

	// Fallback: compute from page element and scaled boxes
	if (!pageElement) {
		return null;
	}

	const pageRect = pageElement.getBoundingClientRect();
	const pdfContainerRect = pdfContainerRef.getBoundingClientRect();

	// Find bounding box extremes
	const topBox = scaledBoxes.reduce((prev, cur) => (cur.y < prev.y ? cur : prev));
	const bottomBox = scaledBoxes.reduce(
		(prev, cur) => (cur.y + cur.height > prev.y + prev.height ? cur : prev)
	);
	const leftBox = scaledBoxes.reduce((prev, cur) => (cur.x < prev.x ? cur : prev));
	const rightBox = scaledBoxes.reduce(
		(prev, cur) => (cur.x + cur.width > prev.x + prev.width ? cur : prev)
	);

	// Calculate positions
	const PDF_PADDING = 16;
	const pageOffsetTop = pageRect.top - scrollRect.top + scrollTop;
	const pageLeftRelativeToContainer = PDF_PADDING;
	const pageLeftRelativeSidebar =
		pdfContainerRect.left - sidebarRect.left + pageLeftRelativeToContainer;

	const leftX = pageLeftRelativeSidebar + leftBox.x;
	const rightX = pageLeftRelativeSidebar + rightBox.x + rightBox.width;
	const top = pageOffsetTop + topBox.y;
	const bottom = pageOffsetTop + bottomBox.y + bottomBox.height;

	return { leftX, rightX, top, bottom };
}

/**
 * Group comments by vertical proximity.
 * Comments within groupThreshold pixels are grouped together.
 */
export function groupCommentsByProximity(
	comments: LocalComment[],
	options: {
		groupThreshold: number;
		hoveredCommentId: number | null;
		focusedCommentId: number | null;
	}
): CommentGroup[] {
	const { groupThreshold, hoveredCommentId, focusedCommentId } = options;

	// Filter comments with valid screen positions and sort by ideal top
	const positioned = comments
		.filter((c) => c.screenPosition !== null)
		.sort((a, b) => {
			const aTop = a.screenPosition!.comment.idealTop;
			const bTop = b.screenPosition!.comment.idealTop;
			return aTop - bTop;
		});

	const groups: CommentGroup[] = [];
	let currentGroup: LocalComment[] = [];

	for (const comment of positioned) {
		if (currentGroup.length === 0) {
			currentGroup.push(comment);
		} else {
			const firstInGroup = currentGroup[0];
			const lastTop = firstInGroup.screenPosition!.comment.idealTop;
			const currentTop = comment.screenPosition!.comment.idealTop;

			// Check if current comment is close enough to group with previous
			if (Math.abs(currentTop - lastTop) <= groupThreshold) {
				currentGroup.push(comment);
			} else {
				// Finalize current group
				groups.push(createGroup(currentGroup, hoveredCommentId, focusedCommentId));
				currentGroup = [comment];
			}
		}
	}

	// Add last group
	if (currentGroup.length > 0) {
		groups.push(createGroup(currentGroup, hoveredCommentId, focusedCommentId));
	}

	return groups;
}

/**
 * Helper: Create a CommentGroup from a list of comments
 */
function createGroup(
	comments: LocalComment[],
	hoveredCommentId: number | null,
	focusedCommentId: number | null
): CommentGroup {
	const commentIds = comments.map((c) => c.id);

	// Calculate average ideal top
	const avgIdealTop =
		comments.reduce((sum, c) => sum + c.screenPosition!.comment.idealTop, 0) / comments.length;

	// Determine active comment (hovered > focused > first)
	let activeCommentId = comments[0].id;
	if (hoveredCommentId && commentIds.includes(hoveredCommentId)) {
		activeCommentId = hoveredCommentId;
	} else if (focusedCommentId && commentIds.includes(focusedCommentId)) {
		activeCommentId = focusedCommentId;
	}

	// Check if group is expanded or hovered
	const isExpanded = commentIds.includes(focusedCommentId ?? -1);
	const isHovered = commentIds.includes(hoveredCommentId ?? -1);

	return {
		id: commentIds.join('-'),
		commentIds,
		activeCommentId,
		idealTop: avgIdealTop,
		actualTop: avgIdealTop, // Will be updated by collision detection
		isExpanded,
		isHovered
	};
}

/**
 * Apply collision detection to groups.
 * Ensures groups don't overlap by adjusting actualTop positions.
 */
export function resolveCollisions(
	groups: CommentGroup[],
	options: {
		minGap: number;
	}
): CommentGroup[] {
	const { minGap } =
		options;
	
	const resolved = groups.map((group) => ({ ...group }));

	for (let i = 0; i < resolved.length; i++) {
		const group = resolved[i];

		if (i === 0) {
			// First group: use ideal position or zero
			group.actualTop = Math.max(0, group.idealTop);
		} else {
			// Calculate previous group's bottom edge
			const prev = resolved[i - 1];
			const prevHeight = prev.element?.getBoundingClientRect().height ?? 0;
			const prevBottom = prev.actualTop + prevHeight + minGap;

			// Position current group at ideal or after previous (whichever is lower)
			group.actualTop = Math.max(group.idealTop, prevBottom);
		}
	}

	return resolved;
}
