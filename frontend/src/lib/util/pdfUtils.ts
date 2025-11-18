import type { BoundingBox } from '$types/pdf';

/**
 * Merge overlapping or adjacent highlight boxes on the same line
 * This improves the visual appearance of multi-word selections
 */
export function mergeHighlightBoxes(boxes: BoundingBox[]): BoundingBox[] {
	if (boxes.length === 0) return [];

	// Sort boxes by y position first, then x position
	const sorted = [...boxes].sort((a, b) => {
		const yDiff = a.y - b.y;
		if (Math.abs(yDiff) > 5) return yDiff; // Use smaller threshold for line detection
		return a.x - b.x;
	});

	const merged: BoundingBox[] = [];
	let current = { ...sorted[0] };

	for (let i = 1; i < sorted.length; i++) {
		const box = sorted[i];

		// Check if boxes are on the same line (y positions are very close)
		// Use the average height as a more reliable threshold
		const avgHeight = (current.height + box.height) / 2;
		const onSameLine = Math.abs(box.y - current.y) <= avgHeight * 0.3;

		// Check if boxes overlap or are adjacent horizontally (with small gap tolerance)
		const xGap = box.x - (current.x + current.width);
		const xOverlap = xGap <= 10; // Allow small gaps between words

		if (onSameLine && xOverlap) {
			// Merge boxes horizontally
			const rightEdge = Math.max(current.x + current.width, box.x + box.width);
			const leftEdge = Math.min(current.x, box.x);
			const topEdge = Math.min(current.y, box.y);
			const bottomEdge = Math.max(current.y + current.height, box.y + box.height);

			current.x = leftEdge;
			current.y = topEdge;
			current.width = rightEdge - leftEdge;
			current.height = bottomEdge - topEdge;
		} else {
			// Boxes are on different lines or not adjacent, save current and start new
			merged.push(current);
			current = { ...box };
		}
	}

	// Don't forget the last box
	merged.push(current);

	return merged;
}
