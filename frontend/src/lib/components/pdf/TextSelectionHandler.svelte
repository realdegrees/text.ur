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
	 * - Free highlight mode: when no selectable text is near the click, the user
	 *   can draw a rectangle to create a highlight without a text anchor
	 *
	 * Coordinate system:
	 * - All handle/button positions are relative to viewerContainer (absolute positioning)
	 * - Bounding boxes are normalized to 0-1 range relative to page dimensions
	 */
	import { documentStore } from '$lib/runes/document.svelte.js';
	import type { Annotation, BoundingBox } from '$api/types';
	import {
		BOX_MERGE_MARGIN,
		BOX_VERTICAL_OVERLAP_THRESHOLD,
		TEXT_ANCHOR_DISTANCE_THRESHOLD,
		FREE_HIGHLIGHT_MIN_SIZE,
		DOUBLE_TAP_TIMEOUT,
		DOUBLE_TAP_DISTANCE
	} from './constants';
	import { pointerState } from '$lib/util/responsive.svelte';

	interface Props {
		viewerContainer: HTMLDivElement | null;
	}

	let { viewerContainer }: Props = $props();

	let isCreating = $state(false);
	let selectionUI = $state<{
		handles: {
			start: { x: number; y: number; height: number };
			end: { x: number; y: number; height: number };
		};
		buttonPosition: { x: number; y: number };
	} | null>(null);
	let pendingSelection = $state<{ text: string; boxes: BoundingBox[] } | null>(null);
	let draggingHandle = $state<'start' | 'end' | null>(null);
	let isSelecting = $state(false);

	// Free highlight mode state (for PDFs without selectable text)
	let isFreeHighlighting = $state(false);
	let freeHighlightStart = $state<{ x: number; y: number } | null>(null);
	let freeHighlightCurrent = $state<{ x: number; y: number } | null>(null);
	let freeHighlightPageNumber = $state<number | null>(null);
	let freeHighlightDisplayRect = $state<{
		x: number;
		y: number;
		width: number;
		height: number;
	} | null>(null);

	// Double-tap tracking for touch free highlight activation
	let lastTapInfo = $state<{ time: number; x: number; y: number } | null>(null);

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
		if (a.page_number !== b.page_number) return false;

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
			page_number: a.page_number,
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

	const getpage_number = (element: Element): number | null => {
		const pageElement = element.closest('[data-page-number]');
		if (!pageElement) return null;
		return parseInt(pageElement.getAttribute('data-page-number') ?? '0', 10);
	};

	const calculateBoundingBoxes = (selection: Selection): BoundingBox[] => {
		if (!viewerContainer || selection.rangeCount === 0) return [];

		const boxes: BoundingBox[] = [];
		const range = selection.getRangeAt(0);
		const container = range.commonAncestorContainer;

		const processTextNode = (node: Text, start: number, end: number) => {
			const element = node.parentElement;
			if (!element) return;

			const page_number = getpage_number(element);
			if (!page_number) return;

			const pageElement = viewerContainer!.querySelector(
				`[data-page-number="${page_number}"]`
			) as HTMLElement | null;
			if (!pageElement) return;

			const textLayer = pageElement.querySelector('.textLayer');
			if (!textLayer) return;

			const textLayerRect = textLayer.getBoundingClientRect();
			if (textLayerRect.width === 0 || textLayerRect.height === 0) return;

			// Create a range for this specific text node segment
			const subRange = document.createRange();
			subRange.setStart(node, start);
			subRange.setEnd(node, end);

			const rects = subRange.getClientRects();

			for (let i = 0; i < rects.length; i++) {
				const rect = rects[i];
				if (rect.width === 0 || rect.height === 0) continue;

				// Normalize coordinates to 0-1 range relative to text layer
				const x = (rect.left - textLayerRect.left) / textLayerRect.width;
				const y = (rect.top - textLayerRect.top) / textLayerRect.height;
				const width = rect.width / textLayerRect.width;
				const height = rect.height / textLayerRect.height;

				boxes.push({
					page_number,
					x: Math.max(0, Math.min(1, x)),
					y: Math.max(0, Math.min(1, y)),
					width: Math.min(1 - Math.max(0, x), width),
					height: Math.min(1 - Math.max(0, y), height)
				});
			}
		};

		if (container.nodeType === Node.TEXT_NODE) {
			processTextNode(container as Text, range.startOffset, range.endOffset);
		} else {
			const treeWalker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, null);

			let currentNode = treeWalker.nextNode();
			let hasStarted = false;

			while (currentNode) {
				const node = currentNode as Text;
				const intersects = range.intersectsNode(node);

				if (intersects) {
					hasStarted = true;
					const start = node === range.startContainer ? range.startOffset : 0;
					const end = node === range.endContainer ? range.endOffset : node.length;

					if (start < end) {
						processTextNode(node, start, end);
					}
				} else if (hasStarted) {
					// We have passed the range
					break;
				}

				currentNode = treeWalker.nextNode();
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
	 * Check if there's a text node within the PDF text layer near the given
	 * viewport coordinates. Returns true if the nearest caret position is
	 * within TEXT_ANCHOR_DISTANCE_THRESHOLD pixels and belongs to a textLayer.
	 */
	const hasTextAnchorAt = (clientX: number, clientY: number): boolean => {
		const range = getCaretPosition(clientX, clientY);
		if (!range) return false;

		const node = range.startContainer;
		const element = node.nodeType === Node.TEXT_NODE ? node.parentElement : (node as Element);
		if (!element) return false;

		const textLayer = element.closest('.textLayer');
		if (!textLayer) return false;

		// Measure distance from click to the caret's bounding rect
		const rangeRect = range.getBoundingClientRect();
		const nearestX = Math.max(rangeRect.left, Math.min(clientX, rangeRect.right));
		const nearestY = Math.max(rangeRect.top, Math.min(clientY, rangeRect.bottom));
		if (Math.hypot(nearestX - clientX, nearestY - clientY) > TEXT_ANCHOR_DISTANCE_THRESHOLD) {
			return false;
		}

		return true;
	};

	/**
	 * Get the PDF page number at the given viewport coordinates.
	 */
	const getPageNumberAt = (clientX: number, clientY: number): number | null => {
		const el = document.elementFromPoint(clientX, clientY);
		if (!el) return null;
		const pageEl = el.closest('[data-page-number]');
		if (!pageEl) return null;
		return parseInt(pageEl.getAttribute('data-page-number') ?? '0', 10);
	};

	/**
	 * Clear all selection UI state
	 */
	const clearSelectionUI = () => {
		selectionUI = null;
		pendingSelection = null;
		freeHighlightDisplayRect = null;
	};

	/**
	 * Clear free highlight drag state and remove the touch-specific move listener
	 * that was registered synchronously on double-tap.
	 */
	const clearFreeHighlight = () => {
		isFreeHighlighting = false;
		freeHighlightStart = null;
		freeHighlightCurrent = null;
		freeHighlightPageNumber = null;
		window.removeEventListener('touchmove', onFreeHighlightMove);
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

		let buttonX: number;
		let buttonY: number;

		if (pointerState.showCustomHandles) {
			// Custom handles visible: position to the right of the selection end
			buttonX = lastRect.right - containerRect.left + 10;
			buttonY = lastRect.bottom - containerRect.top + 10;
		} else {
			// Native teardrops visible: center horizontally, below the last line
			// with extra vertical offset to clear native teardrop handles
			const selectionMidX = (firstRect.left + lastRect.right) / 2 - containerRect.left;
			const containerWidth = containerRect.width;
			const buttonWidth = 180; // approximate button width
			buttonX = Math.max(
				8,
				Math.min(selectionMidX - buttonWidth / 2, containerWidth - buttonWidth - 8)
			);
			buttonY = lastRect.bottom - containerRect.top + 28;
		}

		selectionUI = {
			handles: {
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
			},
			buttonPosition: { x: buttonX, y: buttonY }
		};

		return true;
	};

	/**
	 * Recompute the container-relative position of a confirmed free highlight
	 * rectangle from its normalized bounding box, and position the button.
	 */
	const updateFreeHighlightPositions = (): boolean => {
		if (!viewerContainer || !pendingSelection || pendingSelection.text) return false;

		const box = pendingSelection.boxes[0];
		if (!box) return false;

		const pageElement = viewerContainer.querySelector(
			`[data-page-number="${box.page_number}"]`
		) as HTMLElement | null;
		if (!pageElement) return false;

		const textLayer = pageElement.querySelector('.textLayer') as HTMLElement | null;
		const refEl = textLayer || pageElement;
		const refRect = refEl.getBoundingClientRect();
		const containerRect = viewerContainer.getBoundingClientRect();

		if (refRect.width === 0 || refRect.height === 0) return false;

		const x = refRect.left - containerRect.left + box.x * refRect.width;
		const y = refRect.top - containerRect.top + box.y * refRect.height;
		const width = box.width * refRect.width;
		const height = box.height * refRect.height;

		freeHighlightDisplayRect = { x, y, width, height };

		selectionUI = {
			handles: {
				start: { x, y, height: 0 },
				end: { x: x + width, y: y + height, height: 0 }
			},
			buttonPosition: { x: x + width + 10, y: y + height + 10 }
		};

		return true;
	};

	/**
	 * Update selection state from current DOM selection
	 * Validates selection, calculates bounding boxes, and updates UI
	 */
	const updateSelectionState = () => {
		isSelecting = false;
		if (!viewerContainer || isCreating || isFreeHighlighting) return;

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
				boundingBoxes: pendingSelection.boxes
			};

			const id = await documentStore.comments.create({ annotation, visibility: 'public' });

			window.getSelection()?.removeAllRanges();
			clearSelectionUI();

			if (!id) return;
			documentStore.activeTab = 'comments';
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

		const coords = getEventCoordinates(e);

		// Check if there's selectable text near the click
		if (hasTextAnchorAt(coords.x, coords.y)) {
			isSelecting = true;
			lastTapInfo = null;
			return;
		}

		// No text anchor — check if we're on a PDF page for free highlight
		const pageNumber = getPageNumberAt(coords.x, coords.y);
		if (!pageNumber || !viewerContainer) {
			isSelecting = true;
			lastTapInfo = null;
			return;
		}

		const isTouchEvent = window.TouchEvent && e instanceof TouchEvent;

		if (isTouchEvent) {
			// Touch: require double-tap to start free highlight (single touch scrolls)
			const now = Date.now();
			if (
				lastTapInfo &&
				now - lastTapInfo.time < DOUBLE_TAP_TIMEOUT &&
				Math.hypot(coords.x - lastTapInfo.x, coords.y - lastTapInfo.y) < DOUBLE_TAP_DISTANCE
			) {
				// Double-tap detected — enter free highlight mode
				lastTapInfo = null;
			} else {
				// First tap — record and let browser handle normally (scroll)
				lastTapInfo = { time: now, x: coords.x, y: coords.y };
				return;
			}
		} else {
			// Mouse: single click-drag starts free highlight directly
			e.preventDefault();
		}

		const containerRect = viewerContainer.getBoundingClientRect();
		freeHighlightStart = {
			x: coords.x - containerRect.left,
			y: coords.y - containerRect.top
		};
		freeHighlightCurrent = { ...freeHighlightStart };
		freeHighlightPageNumber = pageNumber;
		isFreeHighlighting = true;
		window.getSelection()?.removeAllRanges();
		clearSelectionUI();

		// For touch: register non-passive touchmove synchronously so the very
		// first touchmove is caught before the browser commits to scrolling.
		if (isTouchEvent) {
			window.addEventListener('touchmove', onFreeHighlightMove, { passive: false });
		}
	};

	/**
	 * Suppress the native context menu on touch devices when a text selection
	 * is active inside the viewer. This prevents the OS copy/paste menu from
	 * overlapping the "Create Annotation" button.  Desktop is left untouched
	 * so right-click still works normally.
	 */
	const onContextMenu = (e: Event) => {
		if (
			pointerState.isTouchInteraction &&
			(selectionUI || pendingSelection || isFreeHighlighting)
		) {
			e.preventDefault();
		}
	};

	// Container-specific event listeners for selection start/end detection and scrolling
	$effect(() => {
		if (!viewerContainer) return;

		// Update handle/rect positions on scroll (without recalculating bounding boxes)
		const onScroll = () => {
			if (pendingSelection && !draggingHandle) {
				if (pendingSelection.text) {
					updateHandlePositions();
				} else {
					updateFreeHighlightPositions();
				}
			}
		};

		viewerContainer.addEventListener('mousedown', onContainerMouseDown);
		viewerContainer.addEventListener('touchstart', onContainerMouseDown, { passive: true });
		viewerContainer.addEventListener('mouseup', updateSelectionState);
		viewerContainer.addEventListener('touchend', updateSelectionState);
		viewerContainer.addEventListener('scroll', onScroll, { passive: true });
		viewerContainer.addEventListener('contextmenu', onContextMenu);
		// Free highlight mousemove on the container (always registered, no-ops when
		// isFreeHighlighting is false). Mouse doesn't have the passive/scroll issue.
		// Touch touchmove is registered synchronously in onContainerMouseDown on
		// double-tap detection to avoid degrading normal scroll performance.
		viewerContainer.addEventListener('mousemove', onFreeHighlightMove);

		return () => {
			viewerContainer.removeEventListener('mousedown', onContainerMouseDown);
			viewerContainer.removeEventListener('touchstart', onContainerMouseDown);
			viewerContainer.removeEventListener('mouseup', updateSelectionState);
			viewerContainer.removeEventListener('touchend', updateSelectionState);
			viewerContainer.removeEventListener('scroll', onScroll);
			viewerContainer.removeEventListener('contextmenu', onContextMenu);
			viewerContainer.removeEventListener('mousemove', onFreeHighlightMove);
			// Also clean up any active touch free highlight listener
			window.removeEventListener('touchmove', onFreeHighlightMove);
		};
	});

	/**
	 * Handle external selection changes: native teardrop adjustments,
	 * keyboard selection, or selection clearing/moving outside viewer.
	 */
	const handleSelectionChange = () => {
		if (draggingHandle || isFreeHighlighting) return;

		const selection = window.getSelection();
		if (!selection || selection.isCollapsed) {
			clearSelectionUI();
			return;
		}

		if (
			!viewerContainer ||
			!selection.anchorNode ||
			!viewerContainer.contains(selection.anchorNode)
		) {
			clearSelectionUI();
			return;
		}

		// While actively selecting (mousedown held), skip full recalculation.
		// The mouseup/touchend handler will trigger it when selection completes.
		if (isSelecting) return;

		// Full recalculation for external changes (native teardrops, keyboard, etc.)
		updateSelectionState();
	};

	/**
	 * Update handle positions on window resize
	 */
	const onResize = () => {
		if (pendingSelection && !draggingHandle) {
			if (pendingSelection.text) {
				updateHandlePositions();
			} else {
				updateFreeHighlightPositions();
			}
		}
	};

	// Global listeners: selection changes, resize, and free highlight release (always active).
	// Free highlight mouseup/touchend is on window so we catch releases outside the container.
	// The handler no-ops when isFreeHighlighting is false.
	$effect(() => {
		document.addEventListener('selectionchange', handleSelectionChange);
		window.addEventListener('resize', onResize, { passive: true });
		window.addEventListener('mouseup', onFreeHighlightUp);
		window.addEventListener('touchend', onFreeHighlightUp);

		return () => {
			document.removeEventListener('selectionchange', handleSelectionChange);
			window.removeEventListener('resize', onResize);
			window.removeEventListener('mouseup', onFreeHighlightUp);
			window.removeEventListener('touchend', onFreeHighlightUp);
		};
	});

	// Handle-drag listeners: only active when custom handles are shown.
	// Re-registers reactively when pointer type changes to ensure drag
	// works correctly on hybrid devices switching between mouse and touch.
	$effect(() => {
		if (!pointerState.showCustomHandles) return;

		window.addEventListener('mousemove', onWindowMove);
		window.addEventListener('touchmove', onWindowMove, { passive: false });
		window.addEventListener('mouseup', onWindowUp);
		window.addEventListener('touchend', onWindowUp);

		return () => {
			window.removeEventListener('mousemove', onWindowMove);
			window.removeEventListener('touchmove', onWindowMove);
			window.removeEventListener('mouseup', onWindowUp);
			window.removeEventListener('touchend', onWindowUp);
		};
	});

	// ============================================================================
	// Free Highlight Dragging
	// ============================================================================

	/**
	 * Track pointer movement while drawing a free highlight rectangle.
	 * Clamps coordinates to the target page boundaries.
	 */
	const onFreeHighlightMove = (e: MouseEvent | TouchEvent) => {
		if (!isFreeHighlighting || !viewerContainer || !freeHighlightPageNumber) return;
		e.preventDefault();

		const coords = getEventCoordinates(e);
		const containerRect = viewerContainer.getBoundingClientRect();

		let x = coords.x - containerRect.left;
		let y = coords.y - containerRect.top;

		// Clamp to the target page boundaries
		const pageElement = viewerContainer.querySelector(
			`[data-page-number="${freeHighlightPageNumber}"]`
		) as HTMLElement | null;
		if (pageElement) {
			const pageRect = pageElement.getBoundingClientRect();
			const pageLeft = pageRect.left - containerRect.left;
			const pageTop = pageRect.top - containerRect.top;
			x = Math.max(pageLeft, Math.min(pageLeft + pageRect.width, x));
			y = Math.max(pageTop, Math.min(pageTop + pageRect.height, y));
		}

		freeHighlightCurrent = { x, y };
	};

	/**
	 * Finalize the free highlight rectangle on pointer release.
	 * Converts the drawn rectangle to a normalized bounding box and
	 * sets up the pending selection + button UI.
	 */
	const onFreeHighlightUp = () => {
		if (
			!isFreeHighlighting ||
			!freeHighlightStart ||
			!freeHighlightCurrent ||
			!freeHighlightPageNumber ||
			!viewerContainer
		) {
			clearFreeHighlight();
			return;
		}

		// Compute rectangle in container-relative coordinates
		const rectWidth = Math.abs(freeHighlightCurrent.x - freeHighlightStart.x);
		const rectHeight = Math.abs(freeHighlightCurrent.y - freeHighlightStart.y);

		// Reject tiny accidental clicks/taps
		if (rectWidth < FREE_HIGHLIGHT_MIN_SIZE || rectHeight < FREE_HIGHLIGHT_MIN_SIZE) {
			clearFreeHighlight();
			return;
		}

		const left = Math.min(freeHighlightStart.x, freeHighlightCurrent.x);
		const top = Math.min(freeHighlightStart.y, freeHighlightCurrent.y);

		// Find the reference element for normalization
		const pageElement = viewerContainer.querySelector(
			`[data-page-number="${freeHighlightPageNumber}"]`
		) as HTMLElement | null;
		if (!pageElement) {
			clearFreeHighlight();
			return;
		}

		const textLayer = pageElement.querySelector('.textLayer') as HTMLElement | null;
		const refEl = textLayer || pageElement;
		const refRect = refEl.getBoundingClientRect();
		const containerRect = viewerContainer.getBoundingClientRect();

		if (refRect.width === 0 || refRect.height === 0) {
			clearFreeHighlight();
			return;
		}

		// Convert container-relative rect to normalized [0-1] coordinates
		const refLeft = refRect.left - containerRect.left;
		const refTop = refRect.top - containerRect.top;

		const normX = (left - refLeft) / refRect.width;
		const normY = (top - refTop) / refRect.height;
		const normW = rectWidth / refRect.width;
		const normH = rectHeight / refRect.height;

		const box: BoundingBox = {
			page_number: freeHighlightPageNumber,
			x: Math.max(0, Math.min(1, normX)),
			y: Math.max(0, Math.min(1, normY)),
			width: Math.min(1 - Math.max(0, normX), normW),
			height: Math.min(1 - Math.max(0, normY), normH)
		};

		pendingSelection = { text: '', boxes: [box] };
		clearFreeHighlight();
		updateFreeHighlightPositions();
	};

	// Toggle dragging class to disable pointer events on highlights during selection
	$effect(() => {
		if (!viewerContainer) return;

		if (draggingHandle || isSelecting || isFreeHighlighting) {
			viewerContainer.classList.add('dragging-selection');
		} else {
			viewerContainer.classList.remove('dragging-selection');
		}
	});

	// Update handle/rect positions when document scale changes
	$effect(() => {
		// Register dependency
		void documentStore.documentScale;

		if (pendingSelection && !draggingHandle) {
			// Use setTimeout to ensure layout has updated
			setTimeout(() => {
				if (pendingSelection?.text) {
					updateHandlePositions();
				} else {
					updateFreeHighlightPositions();
				}
			}, 0);
		}
	});
</script>

<!-- Free highlight rectangle preview (during drag) -->
{#if isFreeHighlighting && freeHighlightStart && freeHighlightCurrent}
	{@const left = Math.min(freeHighlightStart.x, freeHighlightCurrent.x)}
	{@const top = Math.min(freeHighlightStart.y, freeHighlightCurrent.y)}
	{@const w = Math.abs(freeHighlightCurrent.x - freeHighlightStart.x)}
	{@const h = Math.abs(freeHighlightCurrent.y - freeHighlightStart.y)}
	<div
		class="pointer-events-none absolute z-50 rounded-sm border-2 border-blue-500/60 bg-blue-500/15"
		style="top: {top}px; left: {left}px; width: {w}px; height: {h}px;"
	></div>
{/if}

<!-- Confirmed free highlight rectangle (after drag, before annotation creation) -->
{#if freeHighlightDisplayRect}
	<div
		class="pointer-events-none absolute z-50 rounded-sm border-2 border-blue-500/60 bg-blue-500/15"
		style="top: {freeHighlightDisplayRect.y}px; left: {freeHighlightDisplayRect.x}px; width: {freeHighlightDisplayRect.width}px; height: {freeHighlightDisplayRect.height}px;"
	></div>
{/if}

{#if selectionUI}
	<!-- Custom selection handles with drag-to-adjust.
	     Shown on mouse/pen input, or on touch when native handles are unreliable.
	     Hidden on iOS/Android touch where native OS teardrops are used instead.
	     Not shown for free highlights (no text selection to adjust). -->
	{#if pointerState.showCustomHandles && pendingSelection?.text}
		<div
			class="absolute z-1000 w-0.5 cursor-pointer bg-blue-500 {draggingHandle
				? 'pointer-events-none'
				: ''}"
			style="top: {selectionUI.handles.start.y}px; left: {selectionUI.handles.start
				.x}px; height: {selectionUI.handles.start.height}px;"
			onmousedown={(e) => onHandleDown('start', e)}
			use:nonPassiveTouchStart={(e) => onHandleDown('start', e)}
			role="button"
			tabindex="0"
			aria-label="Drag to adjust selection start"
		>
			<div
				class="absolute top-0 animate-ping rounded-l-full bg-blue-500 opacity-75"
				style="left: -{selectionUI.handles.start.height / 2}px; height: {selectionUI.handles.start
					.height}px; width: {selectionUI.handles.start.height / 2}px;"
			></div>
			<div
				class="absolute top-0 rounded-l-full bg-blue-500 shadow-lg"
				style="left: -{selectionUI.handles.start.height / 2}px; height: {selectionUI.handles.start
					.height}px; width: {selectionUI.handles.start.height / 2}px;"
			></div>
		</div>
		<div
			class="absolute z-1000 w-0.5 cursor-pointer bg-blue-500 {draggingHandle
				? 'pointer-events-none'
				: ''}"
			style="top: {selectionUI.handles.end.y}px; left: {selectionUI.handles.end
				.x}px; height: {selectionUI.handles.end.height}px;"
			onmousedown={(e) => onHandleDown('end', e)}
			use:nonPassiveTouchStart={(e) => onHandleDown('end', e)}
			role="button"
			tabindex="0"
			aria-label="Drag to adjust selection end"
		>
			<div
				class="absolute bottom-0 animate-ping rounded-r-full bg-blue-500 opacity-75"
				style="right: -{selectionUI.handles.end.height / 2}px; height: {selectionUI.handles.end
					.height}px; width: {selectionUI.handles.end.height / 2}px;"
			></div>
			<div
				class="absolute bottom-0 rounded-r-full bg-blue-500 shadow-lg"
				style="right: -{selectionUI.handles.end.height / 2}px; height: {selectionUI.handles.end
					.height}px; width: {selectionUI.handles.end.height / 2}px;"
			></div>
		</div>
	{/if}

	<button
		class="absolute z-1000 flex items-center justify-center gap-2 rounded border border-blue-600 bg-blue-500 px-3 py-2 text-white shadow-lg transition-all duration-100 hover:scale-105 hover:bg-blue-600 active:scale-95"
		style="top: {selectionUI.buttonPosition.y}px; left: {selectionUI.buttonPosition.x}px;"
		onmousedown={(e) => e.preventDefault()}
		onclick={createAnnotation}
		aria-label="Add annotation"
	>
		<svg
			xmlns="http://www.w3.org/2000/svg"
			width="18"
			height="18"
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
		<span class="text-sm font-medium whitespace-nowrap">Create Annotation</span>
	</button>
{/if}

<style>
	:global(.dragging-selection .annotation-highlight) {
		pointer-events: none !important;
	}
</style>
