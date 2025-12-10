<script lang="ts">
	/**
	 * TextSelectionHandler - Manages text selection and annotation creation in PDF viewer
	 *
	 * Features:
	 * - Visual selection handles (start/end) with drag-to-adjust
	 * - Create annotation button positioned at selection end
	 * - Bounding box calculation for multi-line selections
	 * - Box merging to reduce visual clutter
	 * - Touch and mouse support
	 *
	 * Coordinate system:
	 * - All handle/button positions are relative to viewerContainer (absolute positioning)
	 * - Bounding boxes are normalized to 0-1 range relative to page dimensions
	 */
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
	let selectionButtonPosition = $state<{ x: number; y: number } | null>(null);
	let selectionHandles = $state<{
		start: { x: number; y: number; height: number };
		end: { x: number; y: number; height: number };
	} | null>(null);
	let pendingSelection = $state<{ text: string; boxes: BoundingBox[] } | null>(null);
	let draggingHandle = $state<'start' | 'end' | null>(null);
	let isSelecting = $state(false);

	// ============================================================================
	// Bounding Box Utilities
	// ============================================================================

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

	// ============================================================================
	// Selection State Management
	// ============================================================================

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

	/**
	 * Get caret position at given viewport coordinates
	 * Handles browser compatibility for caretRangeFromPoint/caretPositionFromPoint
	 */
	const getCaretPosition = (x: number, y: number): Range | null => {
		if (document.caretRangeFromPoint) {
			return document.caretRangeFromPoint(x, y);
		}
		if ((document as any).caretPositionFromPoint) {
			const pos = (document as any).caretPositionFromPoint(x, y);
			const range = document.createRange();
			range.setStart(pos.offsetNode, pos.offset);
			range.collapse(true);
			return range;
		}
		return null;
	};

	/**
	 * Clear all selection UI state
	 */
	const clearSelectionUI = () => {
		selectionButtonPosition = null;
		pendingSelection = null;
		selectionHandles = null;
	};

	/**
	 * Update handle and button positions from current selection rects
	 */
	const updateHandlePositions = () => {
		if (!viewerContainer) return false;

		const selection = window.getSelection();
		if (!selection || selection.isCollapsed) return false;

		const range = selection.getRangeAt(0);
		const rects = range.getClientRects();
		if (rects.length === 0) return false;

		const firstRect = rects[0];
		const lastRect = rects[rects.length - 1];
		const containerRect = viewerContainer.getBoundingClientRect();

		selectionHandles = {
			start: {
				x: firstRect.left - containerRect.left,
				y: firstRect.top - containerRect.top,
				height: firstRect.height
			},
			end: {
				x: lastRect.right - containerRect.left,
				y: lastRect.top - containerRect.top,
				height: lastRect.height
			}
		};

		selectionButtonPosition = {
			x: lastRect.right - containerRect.left + 10,
			y: lastRect.bottom - containerRect.top + 10
		};

		return true;
	};

	/**
	 * Update selection state from current DOM selection
	 * Validates selection, calculates bounding boxes, and updates UI
	 */
	const updateSelectionState = () => {
		isSelecting = false;
		if (!viewerContainer || isCreating) return;

		const selection = window.getSelection();
		if (!selection || selection.isCollapsed) {
			clearSelectionUI();
			return;
		}

		const text = selection.toString().trim();
		if (!text) {
			clearSelectionUI();
			return;
		}

		const anchorNode = selection.anchorNode;
		if (!anchorNode || !viewerContainer.contains(anchorNode as Node)) {
			clearSelectionUI();
			return;
		}

		const boxes = calculateBoundingBoxes(selection);
		if (boxes.length === 0) {
			clearSelectionUI();
			return;
		}

		const mergedBoxes = mergeOverlappingBoxes(boxes);
		pendingSelection = { text, boxes: mergedBoxes };

		updateHandlePositions();
	};

	// ============================================================================
	// Annotation Creation
	// ============================================================================

	const createAnnotation = async () => {
		if (!pendingSelection || isCreating) return;

		isCreating = true;
		try {
			const annotation: Annotation = {
				text: pendingSelection.text,
				boundingBoxes: pendingSelection.boxes,
				color: DEFAULT_HIGHLIGHT_COLOR
			};

			const id = await documentStore.comments.create({ annotation, visibility: 'public' });

			window.getSelection()?.removeAllRanges();
			selectionButtonPosition = null;
			pendingSelection = null;
			selectionHandles = null;

			if (!id) return;
			documentStore.activeCommentId = id;
			const state = documentStore.comments.getState(id);

			state!.isEditing = true;
		} finally {
			isCreating = false;
		}
	};

	// ============================================================================
	// Handle Dragging
	// ============================================================================

	/**
	 * Extract client coordinates from mouse or touch event
	 */
	const getEventCoordinates = (e: MouseEvent | TouchEvent): { x: number; y: number } => {
		if (window.TouchEvent && e instanceof TouchEvent) {
			return { x: e.touches[0].clientX, y: e.touches[0].clientY };
		}
		return { x: (e as MouseEvent).clientX, y: (e as MouseEvent).clientY };
	};

	/**
	 * Start dragging a selection handle
	 * Flips the selection anchor/focus so the dragged end becomes the focus
	 */
	const onHandleDown = (type: 'start' | 'end', e: MouseEvent | TouchEvent) => {
		e.preventDefault();
		e.stopPropagation();

		const selection = window.getSelection();
		if (!selection || selection.rangeCount === 0) {
			draggingHandle = type;
			return;
		}

		const range = selection.getRangeAt(0);
		const isLTR =
			selection.anchorNode === range.startContainer && selection.anchorOffset === range.startOffset;

		// Flip selection if we're dragging the anchor point, making the other end the fixed point
		const shouldFlip = (type === 'start' && isLTR) || (type === 'end' && !isLTR);
		if (shouldFlip) {
			selection.setBaseAndExtent(
				selection.focusNode!,
				selection.focusOffset,
				selection.anchorNode!,
				selection.anchorOffset
			);
		}

		draggingHandle = type;
	};

	/**
	 * Update selection while dragging a handle
	 */
	const onWindowMove = (e: MouseEvent | TouchEvent) => {
		if (!draggingHandle) return;
		e.preventDefault();

		const { x, y } = getEventCoordinates(e);
		const newRange = getCaretPosition(x, y);
		if (!newRange) return;

		const selection = window.getSelection();
		if (!selection || selection.rangeCount === 0) return;

		// Extend selection to new caret position (anchor stays fixed)
		selection.setBaseAndExtent(
			selection.anchorNode!,
			selection.anchorOffset,
			newRange.startContainer,
			newRange.startOffset
		);

		updateSelectionState();
	};

	/**
	 * Stop dragging selection handle
	 */
	const onWindowUp = () => {
		draggingHandle = null;
	};

	// ============================================================================
	// Event Listeners
	// ============================================================================

	/**
	 * Svelte action for non-passive touch events
	 */
	const nonPassiveTouchStart = (node: HTMLElement, callback: (e: TouchEvent) => void) => {
		const handler = (e: TouchEvent) => callback(e);
		node.addEventListener('touchstart', handler, { passive: false });
		return {
			destroy() {
				node.removeEventListener('touchstart', handler);
			}
		};
	};

	const onContainerMouseDown = (e: MouseEvent | TouchEvent) => {
		// If clicking on a highlight, don't start selection mode
		if ((e.target as HTMLElement).closest('.annotation-highlight')) return;
		isSelecting = true;
	};

	// Container-specific event listeners for selection start/end detection and scrolling
	$effect(() => {
		if (!viewerContainer) return;

		// Update handle positions on scroll (without recalculating bounding boxes)
		const onScroll = () => {
			if (pendingSelection && !draggingHandle) {
				updateHandlePositions();
			}
		};

		viewerContainer.addEventListener('mousedown', onContainerMouseDown);
		viewerContainer.addEventListener('touchstart', onContainerMouseDown, { passive: true });
		viewerContainer.addEventListener('mouseup', updateSelectionState);
		viewerContainer.addEventListener('touchend', updateSelectionState);
		viewerContainer.addEventListener('scroll', onScroll, { passive: true });

		return () => {
			viewerContainer.removeEventListener('mousedown', onContainerMouseDown);
			viewerContainer.removeEventListener('touchstart', onContainerMouseDown);
			viewerContainer.removeEventListener('mouseup', updateSelectionState);
			viewerContainer.removeEventListener('touchend', updateSelectionState);
			viewerContainer.removeEventListener('scroll', onScroll);
		};
	});

	// Global event listeners for selection changes and handle dragging
	$effect(() => {
		// Clear UI if selection moves outside viewer container
		const handleSelectionChange = () => {
			if (draggingHandle) return;

			const selection = window.getSelection();
			if (!selection || selection.isCollapsed) {
				clearSelectionUI();
				return;
			}

			if (
				viewerContainer &&
				selection.anchorNode &&
				!viewerContainer.contains(selection.anchorNode)
			) {
				clearSelectionUI();
			}
		};

		// Update handle positions on window resize (without recalculating bounding boxes)
		const onResize = () => {
			if (pendingSelection && !draggingHandle) {
				updateHandlePositions();
			}
		};

		document.addEventListener('selectionchange', handleSelectionChange);
		window.addEventListener('mousemove', onWindowMove);
		window.addEventListener('touchmove', onWindowMove, { passive: false });
		window.addEventListener('mouseup', onWindowUp);
		window.addEventListener('touchend', onWindowUp);
		window.addEventListener('resize', onResize, { passive: true });

		return () => {
			document.removeEventListener('selectionchange', handleSelectionChange);
			window.removeEventListener('mousemove', onWindowMove);
			window.removeEventListener('touchmove', onWindowMove);
			window.removeEventListener('mouseup', onWindowUp);
			window.removeEventListener('touchend', onWindowUp);
			window.removeEventListener('resize', onResize);
		};
	});

	// Toggle dragging class to disable pointer events on highlights during selection
	$effect(() => {
		if (!viewerContainer) return;

		if (draggingHandle || isSelecting) {
			viewerContainer.classList.add('dragging-selection');
		} else {
			viewerContainer.classList.remove('dragging-selection');
		}
	});
</script>

{#if selectionHandles}
	<div
		class="absolute z-1000 w-0.5 cursor-pointer bg-blue-500 {draggingHandle
			? 'pointer-events-none'
			: ''}"
		style="top: {selectionHandles.start.y}px; left: {selectionHandles.start
			.x}px; height: {selectionHandles.start.height}px;"
		onmousedown={(e) => onHandleDown('start', e)}
		use:nonPassiveTouchStart={(e) => onHandleDown('start', e)}
		role="button"
		tabindex="0"
		aria-label="Drag to adjust selection start"
	>
		<div
			class="absolute top-0 animate-ping rounded-l-full bg-blue-500 opacity-75"
			style="left: -{selectionHandles.start.height / 2}px; height: {selectionHandles.start
				.height}px; width: {selectionHandles.start.height / 2}px;"
		></div>
		<div
			class="absolute top-0 rounded-l-full bg-blue-500 shadow-lg"
			style="left: -{selectionHandles.start.height / 2}px; height: {selectionHandles.start
				.height}px; width: {selectionHandles.start.height / 2}px;"
		></div>
	</div>
	<div
		class="absolute z-1000 w-0.5 cursor-pointer bg-blue-500 {draggingHandle
			? 'pointer-events-none'
			: ''}"
		style="top: {selectionHandles.end.y}px; left: {selectionHandles.end
			.x}px; height: {selectionHandles.end.height}px;"
		onmousedown={(e) => onHandleDown('end', e)}
		use:nonPassiveTouchStart={(e) => onHandleDown('end', e)}
		role="button"
		tabindex="0"
		aria-label="Drag to adjust selection end"
	>
		<div
			class="absolute bottom-0 animate-ping rounded-r-full bg-blue-500 opacity-75"
			style="right: -{selectionHandles.end.height / 2}px; height: {selectionHandles.end
				.height}px; width: {selectionHandles.end.height / 2}px;"
		></div>
		<div
			class="absolute bottom-0 rounded-r-full bg-blue-500 shadow-lg"
			style="right: -{selectionHandles.end.height / 2}px; height: {selectionHandles.end
				.height}px; width: {selectionHandles.end.height / 2}px;"
		></div>
	</div>
{/if}

{#if selectionButtonPosition}
	<button
		class="absolute z-1000 flex items-center justify-center rounded border border-blue-600 bg-blue-500 p-2 text-white shadow-lg transition-all duration-100 hover:scale-105 hover:bg-blue-600 active:scale-95"
		style="top: {selectionButtonPosition.y}px; left: {selectionButtonPosition.x}px;"
		onmousedown={(e) => e.preventDefault()}
		onclick={createAnnotation}
		aria-label="Add annotation"
	>
		<svg
			xmlns="http://www.w3.org/2000/svg"
			width="20"
			height="20"
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			stroke-width="2"
			stroke-linecap="round"
			stroke-linejoin="round"
		>
			<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
			<line x1="9" y1="10" x2="15" y2="10"></line>
			<line x1="12" y1="7" x2="12" y2="13"></line>
		</svg>
	</button>
{/if}

<style>
	:global(.dragging-selection .annotation-highlight) {
		pointer-events: none !important;
	}
</style>
