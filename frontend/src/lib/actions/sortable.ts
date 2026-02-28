/**
 * Reusable drag-and-drop sortable action for any list layout.
 *
 * Works with vertical lists, horizontal lists, and wrapped flex layouts
 * — the layout is detected automatically per-item, so a single wrapped
 * container can have horizontal flow within rows and vertical flow
 * between rows.
 *
 * Uses **Pointer Events** so it works identically with mouse, touch,
 * and pen input — no HTML5 Drag and Drop API.
 *
 * Attach to a container element whose direct children are the sortable
 * items.  Each child must have `data-sortable-id` set to a unique
 * identifier.  A drag-handle element inside each child should have
 * `[data-drag-handle]` — only that element will initiate the drag.
 *
 * A semi-transparent **ghost clone** of the dragged item is inserted
 * into the DOM at the target drop position so surrounding items
 * reflow naturally — giving a real-time preview of the final layout.
 * The original dragged item collapses to zero height while dragging.
 *
 * When the pointer is near the top or bottom edge of the nearest
 * scrollable ancestor the list auto-scrolls.
 *
 * @example
 * ```svelte
 * <div use:sortable={{ onReorder }}>
 *   {#each items as item (item.id)}
 *     <div data-sortable-id={item.id}>
 *       <span data-drag-handle class="cursor-grab">⠿</span>
 *       {item.label}
 *     </div>
 *   {/each}
 * </div>
 * ```
 */

export type SortableParams = {
	/** Called after a successful drop with the old and new indices. */
	onReorder: (fromIndex: number, toIndex: number) => void;
	/** Whether sorting is currently enabled (default true). */
	enabled?: boolean;
};

const DRAGGING_CLASS = 'sortable-dragging';
const GHOST_ATTR = 'data-sortable-ghost';
const DRAG_THRESHOLD = 5; // px before a pointer move becomes a drag
const SCROLL_EDGE = 40; // px from edge to start auto-scrolling
const SCROLL_MAX_SPEED = 12; // px per frame at edge

export function sortable(node: HTMLElement, params: SortableParams) {
	let onReorder = params.onReorder;
	let enabled = params.enabled ?? true;

	// ── Pointer / drag state ────────────────────────────────────────

	let pointerId: number | null = null;
	let startX = 0;
	let startY = 0;
	let isDragging = false;

	let draggedId: string | null = null;
	let draggedIndex: number = -1;
	let draggedItem: HTMLElement | null = null;
	let currentInsertionPoint: number = -1;
	let currentToIndex: number = -1;

	// Ghost state
	let ghost: HTMLElement | null = null;

	// Auto-scroll state
	let scrollParent: HTMLElement | null = null;
	let scrollRafId: number | null = null;
	let scrollSpeed = 0;

	// ── Touch-action on handles ─────────────────────────────────────

	function applyHandleTouchAction() {
		const handles = node.querySelectorAll<HTMLElement>('[data-drag-handle]');
		for (const h of handles) {
			h.style.touchAction = enabled ? 'none' : '';
		}
	}

	applyHandleTouchAction();

	const handleObserver = new MutationObserver(applyHandleTouchAction);
	handleObserver.observe(node, { childList: true, subtree: true });

	// ── Helpers ──────────────────────────────────────────────────────

	function getItems(): HTMLElement[] {
		return Array.from(node.children).filter(
			(el): el is HTMLElement =>
				el instanceof HTMLElement &&
				el.hasAttribute('data-sortable-id') &&
				!el.hasAttribute(GHOST_ATTR)
		);
	}

	function getItemId(el: HTMLElement): string | null {
		return el.getAttribute('data-sortable-id');
	}

	/** Check whether two rects occupy the same visual row. */
	function isSameRow(a: DOMRect, b: DOMRect): boolean {
		return Math.abs(a.top - b.top) < Math.min(a.height, b.height) / 2;
	}

	/**
	 * Check whether the item at `index` shares its row with at least
	 * one neighbour.  Items alone on their row use Y-midpoint logic
	 * (vertical-list behaviour).
	 */
	function isOnSharedRow(rects: DOMRect[], index: number): boolean {
		if (index > 0 && isSameRow(rects[index], rects[index - 1])) return true;
		if (index < rects.length - 1 && isSameRow(rects[index], rects[index + 1])) return true;
		return false;
	}

	/**
	 * Determine the insertion point from the pointer position.
	 *
	 * For items that share a row with a neighbour the X-midpoint
	 * decides before/after.  For items alone on their row the
	 * Y-midpoint decides (vertical-list behaviour).
	 *
	 * Returns an index in the items array (excluding the ghost):
	 *   0            → before items[0]
	 *   n            → before items[n]
	 *   items.length → after the last item
	 */
	function computeInsertionPoint(clientX: number, clientY: number): number {
		const items = getItems();
		const rects = items.map((el) => el.getBoundingClientRect());

		for (let i = 0; i < items.length; i++) {
			const r = rects[i];

			// Skip collapsed dragged item (zero-height rect).
			if (r.height === 0) continue;

			// Cursor is above this item entirely → insert before it.
			if (clientY < r.top) return i;

			// Cursor is below this item entirely → continue.
			if (clientY > r.bottom) continue;

			// Cursor overlaps this item's Y range.
			if (isOnSharedRow(rects, i)) {
				// Horizontal flow: use X midpoint.
				if (clientX <= r.left + r.width / 2) return i;
			} else {
				// Alone on row (vertical flow): use Y midpoint.
				if (clientY <= r.top + r.height / 2) return i;
			}
		}

		return items.length;
	}

	/**
	 * Convert an insertion point to the splice-based `toIndex`
	 * expected by `onReorder(fromIndex, toIndex)`.
	 *
	 * Contract:
	 *   const [item] = arr.splice(fromIndex, 1);
	 *   arr.splice(toIndex, 0, item);
	 */
	function spliceIndex(insertionPoint: number): number {
		return insertionPoint > draggedIndex ? insertionPoint - 1 : insertionPoint;
	}

	// ── Ghost element ──────────────────────────────────────────────

	function createGhost(item: HTMLElement): HTMLElement {
		const rect = item.getBoundingClientRect();
		const clone = item.cloneNode(true) as HTMLElement;

		clone.setAttribute(GHOST_ATTR, '');
		clone.classList.remove(DRAGGING_CLASS);
		clone.removeAttribute('data-sortable-id');

		Object.assign(clone.style, {
			width: `${rect.width}px`,
			height: `${rect.height}px`,
			boxSizing: 'border-box',
			flex: '0 0 auto',
			opacity: '0.35',
			pointerEvents: 'none',
			border: '2px dashed var(--color-primary, #3b82f6)',
			borderRadius: getComputedStyle(item).borderRadius
		});

		return clone;
	}

	function insertGhostAt(ip: number) {
		if (!ghost) return;

		const items = getItems();

		if (items.length === 0) {
			node.appendChild(ghost);
		} else if (ip <= 0) {
			node.insertBefore(ghost, items[0]);
		} else if (ip >= items.length) {
			items[items.length - 1].after(ghost);
		} else {
			node.insertBefore(ghost, items[ip]);
		}
	}

	function removeGhost() {
		if (ghost) {
			ghost.remove();
			ghost = null;
		}
	}

	// ── Collapse / expand the dragged item ─────────────────────────

	function collapseItem(item: HTMLElement) {
		item.style.display = 'none';
	}

	function expandItem(item: HTMLElement) {
		item.style.removeProperty('display');
	}

	// ── Auto-scroll ─────────────────────────────────────────────────

	function findScrollParent(el: HTMLElement): HTMLElement | null {
		let parent = el.parentElement;
		while (parent) {
			const { overflowY } = getComputedStyle(parent);
			if (overflowY === 'auto' || overflowY === 'scroll') return parent;
			parent = parent.parentElement;
		}
		return null;
	}

	function updateAutoScroll(clientY: number) {
		if (!scrollParent) return;

		const rect = scrollParent.getBoundingClientRect();
		const distTop = clientY - rect.top;
		const distBottom = rect.bottom - clientY;

		if (distTop < SCROLL_EDGE && scrollParent.scrollTop > 0) {
			// Near top edge — scroll up (negative speed).
			scrollSpeed = -SCROLL_MAX_SPEED * (1 - distTop / SCROLL_EDGE);
		} else if (
			distBottom < SCROLL_EDGE &&
			scrollParent.scrollTop < scrollParent.scrollHeight - scrollParent.clientHeight
		) {
			// Near bottom edge — scroll down (positive speed).
			scrollSpeed = SCROLL_MAX_SPEED * (1 - distBottom / SCROLL_EDGE);
		} else {
			scrollSpeed = 0;
		}

		if (scrollSpeed !== 0 && scrollRafId === null) {
			scrollRafId = requestAnimationFrame(scrollTick);
		}
	}

	function scrollTick() {
		if (!scrollParent || scrollSpeed === 0 || !isDragging) {
			scrollRafId = null;
			return;
		}
		scrollParent.scrollTop += scrollSpeed;
		scrollRafId = requestAnimationFrame(scrollTick);
	}

	function stopAutoScroll() {
		scrollSpeed = 0;
		if (scrollRafId !== null) {
			cancelAnimationFrame(scrollRafId);
			scrollRafId = null;
		}
	}

	// ── Pointer handlers ────────────────────────────────────────────

	function handlePointerDown(e: PointerEvent) {
		if (!enabled || isDragging) return;

		const handle = (e.target as HTMLElement).closest<HTMLElement>('[data-drag-handle]');
		if (!handle) return;

		const item = handle.closest<HTMLElement>('[data-sortable-id]');
		if (!item || !node.contains(item)) return;

		e.preventDefault();

		pointerId = e.pointerId;
		startX = e.clientX;
		startY = e.clientY;

		draggedItem = item;
		draggedId = getItemId(item);
		draggedIndex = getItems().findIndex((el) => getItemId(el) === draggedId);

		node.setPointerCapture(e.pointerId);
	}

	function handlePointerMove(e: PointerEvent) {
		if (pointerId === null || e.pointerId !== pointerId) return;

		const dx = e.clientX - startX;
		const dy = e.clientY - startY;

		if (!isDragging) {
			// Check movement threshold before starting a drag.
			if (Math.sqrt(dx * dx + dy * dy) < DRAG_THRESHOLD) return;
			startDrag();
		}

		// Update ghost position.
		const ip = computeInsertionPoint(e.clientX, e.clientY);

		if (ip !== currentInsertionPoint) {
			currentInsertionPoint = ip;
			currentToIndex = spliceIndex(ip);
			insertGhostAt(ip);
		}

		// Auto-scroll when near edges.
		updateAutoScroll(e.clientY);
	}

	function handlePointerUp(e: PointerEvent) {
		if (pointerId === null || e.pointerId !== pointerId) return;

		if (isDragging) {
			const fromIndex = draggedIndex;
			const toIndex = currentToIndex;

			cleanup();

			if (fromIndex !== -1 && toIndex !== -1 && fromIndex !== toIndex) {
				onReorder(fromIndex, toIndex);
			}
		} else {
			// Pointer released before threshold — not a drag.
			resetPointerState();
		}
	}

	function handlePointerCancel(e: PointerEvent) {
		if (pointerId === null || e.pointerId !== pointerId) return;
		cleanup();
	}

	function handleKeyDown(e: KeyboardEvent) {
		if (e.key === 'Escape' && isDragging) {
			e.preventDefault();
			cleanup();
		}
	}

	// ── Drag lifecycle ──────────────────────────────────────────────

	function startDrag() {
		if (!draggedItem) return;

		isDragging = true;
		draggedItem.classList.add(DRAGGING_CLASS);

		// Prevent text selection while dragging.
		document.body.style.userSelect = 'none';

		// Find scroll parent for auto-scroll.
		scrollParent = findScrollParent(node);

		// Create ghost at the original position, then collapse the
		// original.  The ghost immediately takes its place so there
		// is no visual gap.
		ghost = createGhost(draggedItem);
		currentInsertionPoint = draggedIndex;
		currentToIndex = draggedIndex;
		insertGhostAt(draggedIndex);
		collapseItem(draggedItem);

		window.addEventListener('keydown', handleKeyDown);
	}

	function resetPointerState() {
		if (pointerId !== null) {
			try {
				node.releasePointerCapture(pointerId);
			} catch {
				// Pointer capture may already be released.
			}
		}
		pointerId = null;
		draggedId = null;
		draggedIndex = -1;
		draggedItem = null;
	}

	function cleanup() {
		stopAutoScroll();
		removeGhost();

		if (draggedItem) {
			expandItem(draggedItem);
			draggedItem.classList.remove(DRAGGING_CLASS);
		}

		isDragging = false;
		currentInsertionPoint = -1;
		currentToIndex = -1;

		document.body.style.removeProperty('user-select');
		window.removeEventListener('keydown', handleKeyDown);

		resetPointerState();
	}

	// ── Bind & lifecycle ────────────────────────────────────────────

	node.addEventListener('pointerdown', handlePointerDown);
	node.addEventListener('pointermove', handlePointerMove);
	node.addEventListener('pointerup', handlePointerUp);
	node.addEventListener('pointercancel', handlePointerCancel);

	return {
		update(newParams: SortableParams) {
			onReorder = newParams.onReorder;
			enabled = newParams.enabled ?? true;
			if (!enabled) cleanup();
			applyHandleTouchAction();
		},
		destroy() {
			cleanup();
			handleObserver.disconnect();
			node.removeEventListener('pointerdown', handlePointerDown);
			node.removeEventListener('pointermove', handlePointerMove);
			node.removeEventListener('pointerup', handlePointerUp);
			node.removeEventListener('pointercancel', handlePointerCancel);
			// Restore touch-action on handles.
			const handles = node.querySelectorAll<HTMLElement>('[data-drag-handle]');
			for (const h of handles) {
				h.style.removeProperty('touch-action');
			}
		}
	};
}
