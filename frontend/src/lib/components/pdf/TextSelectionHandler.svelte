<script lang="ts">
	import { documentStore } from '$lib/runes/document.svelte.js';
	import type { Annotation, BoundingBox } from '$types/pdf';
	import {
		BOX_MERGE_MARGIN,
		BOX_VERTICAL_OVERLAP_THRESHOLD,
		DEFAULT_HIGHLIGHT_COLOR
	} from './constants';

	interface Props {
		viewerContainer: HTMLDivElement | null;
	}

	let { viewerContainer }: Props = $props();

	let isCreating = $state(false);

	/**
	 * Check if two boxes should be merged:
	 * - Must be on the same page
	 * - Must be on the same line (similar Y position and height)
	 * - Must be horizontally adjacent or overlapping (with margin)
	 */
	const shouldMergeBoxes = (a: BoundingBox, b: BoundingBox): boolean => {
		if (a.pageNumber !== b.pageNumber) return false;

		// Check if boxes are on the same line (Y positions and heights are similar)
		const aTop = a.y;
		const aBottom = a.y + a.height;
		const bTop = b.y;
		const bBottom = b.y + b.height;

		// Calculate vertical overlap
		const overlapTop = Math.max(aTop, bTop);
		const overlapBottom = Math.min(aBottom, bBottom);
		const verticalOverlap = overlapBottom - overlapTop;

		// Boxes must have significant vertical overlap
		const minHeight = Math.min(a.height, b.height);
		if (verticalOverlap < minHeight * BOX_VERTICAL_OVERLAP_THRESHOLD) return false;

		// Check horizontal adjacency (with margin)
		const aLeft = a.x - BOX_MERGE_MARGIN;
		const aRight = a.x + a.width + BOX_MERGE_MARGIN;
		const bLeft = b.x - BOX_MERGE_MARGIN;
		const bRight = b.x + b.width + BOX_MERGE_MARGIN;

		// Boxes must be horizontally adjacent or overlapping
		return !(aRight < bLeft || bRight < aLeft);
	};

	/**
	 * Merge two boxes on the same line into one
	 */
	const mergeBoxes = (a: BoundingBox, b: BoundingBox): BoundingBox => {
		const left = Math.min(a.x, b.x);
		const top = Math.min(a.y, b.y);
		const right = Math.max(a.x + a.width, b.x + b.width);
		const bottom = Math.max(a.y + a.height, b.y + b.height);

		return {
			pageNumber: a.pageNumber,
			x: left,
			y: top,
			width: right - left,
			height: bottom - top
		};
	};

	/**
	 * Merge adjacent boxes on the same line to reduce visual clutter
	 */
	const mergeOverlappingBoxes = (boxes: BoundingBox[]): BoundingBox[] => {
		if (boxes.length <= 1) return boxes;

		const merged: BoundingBox[] = [];

		for (const box of boxes) {
			let wasMerged = false;

			for (let i = 0; i < merged.length; i++) {
				if (shouldMergeBoxes(merged[i], box)) {
					merged[i] = mergeBoxes(merged[i], box);
					wasMerged = true;
					break;
				}
			}

			if (!wasMerged) {
				merged.push({ ...box });
			}
		}

		// Repeat until no more merges happen (boxes merged in first pass might now overlap)
		if (merged.length < boxes.length) {
			return mergeOverlappingBoxes(merged);
		}

		return merged;
	};

	const getPageNumber = (element: Element): number | null => {
		const pageElement = element.closest('[data-page-number]');
		if (!pageElement) return null;
		return parseInt(pageElement.getAttribute('data-page-number') ?? '0', 10);
	};

	const calculateBoundingBoxes = (selection: Selection): BoundingBox[] => {
		if (!viewerContainer || selection.rangeCount === 0) return [];

		const boxes: BoundingBox[] = [];
		const range = selection.getRangeAt(0);
		const rects = range.getClientRects();

		for (let i = 0; i < rects.length; i++) {
			const rect = rects[i];

			// Try multiple points inside each rect to find one that falls inside the text layer.
			const samplePoints = [
				{ x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 }, // center
				{ x: rect.left + 1, y: rect.top + 1 }, // top-left inset
				{ x: rect.left + rect.width - 1, y: rect.top + 1 }, // top-right inset
				{ x: rect.left + 1, y: rect.top + rect.height - 1 } // bottom-left inset
			];

			let elementAtPoint: Element | null = null;
			for (const p of samplePoints) {
				const el = document.elementFromPoint(p.x, p.y);
				if (!el) continue;
				// Prefer elements from the textLayer so we avoid sampling the canvas/background
				if (el.closest && el.closest('.textLayer')) {
					elementAtPoint = el;
					break;
				}
				// Still accept an element if it has a page wrapper but not a textLayer—
				// this is a fallback to resolve page number for edge cases
				if (el.closest && el.closest('[data-page-number]')) {
					elementAtPoint = el;
					break;
				}
			}

			if (!elementAtPoint) continue;

			const pageNumber = getPageNumber(elementAtPoint);
			if (!pageNumber) continue;

			const pageElement = viewerContainer.querySelector(
				`[data-page-number="${pageNumber}"]`
			) as HTMLElement | null;
			if (!pageElement) continue;

			const canvas = pageElement.querySelector('canvas');
			if (!canvas) continue;

			const textLayer = pageElement.querySelector('.textLayer') as HTMLElement | null;
			if (!textLayer) continue;

			// Use the text layer as the reference frame since that's where the text selection comes from
			const textLayerRect = textLayer.getBoundingClientRect();

			// Guard against degenerate text layers
			if (textLayerRect.width === 0 || textLayerRect.height === 0) continue;

			// If the rect is nearly the size of the entire text layer, ignore it —
			// this is typically the cause of full-page highlights when the
			// selection range produces a block-level bounding rect.
			const fullWidthRatio = rect.width / textLayerRect.width;
			const fullHeightRatio = rect.height / textLayerRect.height;
			const FULL_PAGE_THRESHOLD = 0.95; // 95% of the text layer
			if (fullWidthRatio >= FULL_PAGE_THRESHOLD && fullHeightRatio >= FULL_PAGE_THRESHOLD) continue;

			// Normalize coordinates to 0-1 range relative to text layer
			const x = (rect.left - textLayerRect.left) / textLayerRect.width;
			const y = (rect.top - textLayerRect.top) / textLayerRect.height;
			const width = rect.width / textLayerRect.width;
			const height = rect.height / textLayerRect.height;

			// Only add valid boxes
			if (x >= 0 && y >= 0 && width > 0 && height > 0) {
				boxes.push({
					pageNumber,
					x: Math.max(0, Math.min(1, x)),
					y: Math.max(0, Math.min(1, y)),
					width: Math.min(1 - Math.max(0, x), width),
					height: Math.min(1 - Math.max(0, y), height)
				});
			}
		}

		return boxes;
	};

	const handleMouseUp = async () => {
		if (!viewerContainer || isCreating) return;

		const selection = window.getSelection();
		if (!selection || selection.isCollapsed) return;

		const text = selection.toString().trim();
		if (!text) return;

		// Check if selection is within the PDF viewer
		const anchorNode = selection.anchorNode;
		if (!anchorNode || !viewerContainer.contains(anchorNode as Node)) return;

		const boxes = calculateBoundingBoxes(selection);
		if (boxes.length === 0) return;

		// Merge overlapping boxes to reduce visual clutter
		const mergedBoxes = mergeOverlappingBoxes(boxes);

		// Instantly create the annotation
		isCreating = true;
		try {
			const annotation: Annotation = {
				text,
				boundingBoxes: mergedBoxes,
				color: DEFAULT_HIGHLIGHT_COLOR
			};
			
			const id = await documentStore.comments.create({ annotation, visibility: 'public' });
			// Clear selection after creating
			window.getSelection()?.removeAllRanges();
						
			if (!id) return;
			const state = documentStore.comments.getState(id);
			
			// Pin the new comment and trigger edit mode
			state!.isEditing = true;
		} finally {
			isCreating = false;
		}
	};

	$effect(() => {
		if (viewerContainer) {
			viewerContainer.addEventListener('mouseup', handleMouseUp);
			return () => {
				viewerContainer.removeEventListener('mouseup', handleMouseUp);
			};
		}
	});
</script>

<!-- This component handles text selection and creates annotations instantly -->
