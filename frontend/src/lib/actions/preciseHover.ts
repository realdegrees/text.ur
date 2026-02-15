import { hasHoverCapability } from '$lib/util/responsive.svelte';

type Params = { onEnter?: () => void; onLeave?: () => void };

type Registration = {
	node: HTMLElement;
	params: Params;
	hovered: boolean;
};

// Single global listener shared by all preciseHover instances.
// Calls document.elementFromPoint() once per pointermove event
// and walks the DOM ancestry to dispatch enter/leave to all
// registered nodes, instead of N separate listeners each calling
// elementFromPoint().
const registrations = new Set<Registration>();
let listening = false;
let rafId: number | null = null;
let lastX = 0;
let lastY = 0;

function processHover() {
	rafId = null;

	if (!hasHoverCapability()) return;

	const el = document.elementFromPoint(lastX, lastY);

	for (const reg of registrations) {
		const isTopMost = el === reg.node || reg.node.contains(el);

		if (isTopMost && !reg.hovered) {
			reg.hovered = true;
			reg.params.onEnter?.();
		} else if (!isTopMost && reg.hovered) {
			reg.hovered = false;
			reg.params.onLeave?.();
		}
	}
}

function onGlobalMove(e: PointerEvent) {
	lastX = e.clientX;
	lastY = e.clientY;
	// Coalesce pointermove events into a single RAF callback (~60Hz max)
	if (rafId === null) {
		rafId = requestAnimationFrame(processHover);
	}
}

function ensureListener() {
	if (!listening) {
		window.addEventListener('pointermove', onGlobalMove);
		listening = true;
	}
}

function maybeRemoveListener() {
	if (registrations.size === 0 && listening) {
		window.removeEventListener('pointermove', onGlobalMove);
		if (rafId !== null) {
			cancelAnimationFrame(rafId);
			rafId = null;
		}
		listening = false;
	}
}

export function preciseHover(node: HTMLElement, params: Params) {
	const reg: Registration = { node, params, hovered: false };
	registrations.add(reg);
	ensureListener();

	return {
		destroy() {
			// Fire leave if still hovered when destroyed
			if (reg.hovered) {
				reg.hovered = false;
				reg.params.onLeave?.();
			}
			registrations.delete(reg);
			maybeRemoveListener();
		},
		update(newParams: Params) {
			reg.params = newParams;
		}
	};
}
