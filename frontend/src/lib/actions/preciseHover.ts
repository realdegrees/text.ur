type Params = { onEnter?: () => void; onLeave?: () => void }

export function preciseHover(
  node: HTMLElement,
  params: Params
) {
  let hovered = false;

  function onMove(e: PointerEvent) {
    const el = document.elementFromPoint(e.clientX, e.clientY);

    const isTopMost = el === node || node.contains(el);

    if (isTopMost && !hovered) {
      hovered = true;
      params.onEnter?.();
    }

    if (!isTopMost && hovered) {
      hovered = false;
      params.onLeave?.();
    }
  }

  window.addEventListener("pointermove", onMove);

  return {
    destroy() {
      window.removeEventListener("pointermove", onMove);
    },
    update(newParams: Params) {
      params = newParams;
    }
  };
}
