type Params = {
	onLongPress?: () => void;
	onRelease?: () => void;
	duration?: number; // milliseconds
};

/**
 * Long press action for touch devices
 * Triggers onLongPress after holding for specified duration
 */
export function longPress(node: HTMLElement, params: Params) {
	const duration = params.duration ?? 500; // Default 500ms
	let timer: ReturnType<typeof setTimeout> | null = null;
	let isLongPressing = false;
	let wasLongPress = false; // Track if the last interaction was a long press

	function handleStart(e: PointerEvent) {
		// Only handle touch/pen events (not mouse)
		if (e.pointerType === 'mouse') return;

		isLongPressing = false;
		wasLongPress = false;
		timer = setTimeout(() => {
			isLongPressing = true;
			wasLongPress = true;
			params.onLongPress?.();
		}, duration);
	}

	function handleEnd() {
		if (timer) {
			clearTimeout(timer);
			timer = null;
		}

		if (isLongPressing) {
			isLongPressing = false;
			params.onRelease?.();
		}

		// Reset wasLongPress after a short delay to allow click event to check it
		setTimeout(() => {
			wasLongPress = false;
		}, 100);
	}

	function handleCancel() {
		if (timer) {
			clearTimeout(timer);
			timer = null;
		}

		if (isLongPressing) {
			isLongPressing = false;
			params.onRelease?.();
		}

		wasLongPress = false;
	}

	// Prevent click events after long press
	function handleClick(e: Event) {
		if (wasLongPress) {
			e.preventDefault();
			e.stopPropagation();
		}
	}

	node.addEventListener('pointerdown', handleStart);
	node.addEventListener('pointerup', handleEnd);
	node.addEventListener('pointercancel', handleCancel);
	node.addEventListener('pointermove', handleCancel); // Cancel on move
	node.addEventListener('click', handleClick, true); // Use capture phase to intercept click

	return {
		destroy() {
			if (timer) {
				clearTimeout(timer);
			}
			node.removeEventListener('pointerdown', handleStart);
			node.removeEventListener('pointerup', handleEnd);
			node.removeEventListener('pointercancel', handleCancel);
			node.removeEventListener('pointermove', handleCancel);
			node.removeEventListener('click', handleClick, true);
		},
		update(newParams: Params) {
			params = newParams;
		}
	};
}
