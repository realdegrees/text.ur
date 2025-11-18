import type { CommentRead } from '$api/types';
import type { Annotation } from '$types/pdf';

interface PositionedComment {
	comment: CommentRead;
	idealTop: number;
	actualTop: number;
	rightEdge: number;
}

/**
 * Calculate ideal vertical position for a comment based on its annotation
 */
export function getIdealCommentTopPosition(
	comment: CommentRead,
	textLayerHeight: number
): number {
	const annotation = comment.annotation as unknown as Annotation;
	if (!annotation || !annotation.boundingBoxes || annotation.boundingBoxes.length === 0) {
		return 0;
	}

	// Find the topmost bounding box
	const topBox = annotation.boundingBoxes.reduce((prev, curr) => {
		return curr.y < prev.y ? curr : prev;
	});

	// Convert normalized position to pixels (relative to text layer)
	return topBox.y * textLayerHeight;
}

/**
 * Calculate non-overlapping positions for all comments on a page
 */
export function calculatePositionedComments(
	comments: CommentRead[],
	textLayerHeight: number,
	textLayerWidth: number,
	getHighlightRightEdge: (comment: CommentRead) => number
): PositionedComment[] {
	const COMMENT_HEIGHT = 60; // Approximate height of each comment
	const MIN_GAP = 8; // Minimum gap between comments

	// Sort by ideal position
	const sorted = comments
		.map((comment) => ({
			comment,
			idealTop: getIdealCommentTopPosition(comment, textLayerHeight),
			actualTop: 0,
			rightEdge: getHighlightRightEdge(comment)
		}))
		.sort((a, b) => a.idealTop - b.idealTop);

	// Apply overlap protection
	for (let i = 0; i < sorted.length; i++) {
		if (i === 0) {
			sorted[i].actualTop = sorted[i].idealTop;
		} else {
			const prevBottom = sorted[i - 1].actualTop + COMMENT_HEIGHT + MIN_GAP;
			sorted[i].actualTop = Math.max(sorted[i].idealTop, prevBottom);
		}
	}

	return sorted;
}
