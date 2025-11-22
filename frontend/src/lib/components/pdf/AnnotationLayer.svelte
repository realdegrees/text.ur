<script lang="ts">
	import { documentStore, type CachedComment } from '$lib/runes/document.svelte.js';
	import { parseAnnotation, type Annotation, type BoundingBox } from '$types/pdf';
	import { SvelteMap } from 'svelte/reactivity';
	import { RENDER_DEBOUNCE_MS, OPACITY_TRANSITION_MS } from './constants';

	interface Props {
		viewerContainer: HTMLDivElement | null;
		scale: number;
	}

	let { viewerContainer, scale }: Props = $props();

	// Get comments with valid parsed annotations from the store
	// Only track annotation data, not interaction state (to avoid re-rendering on hover)
	let commentsWithAnnotations = $derived(
		documentStore.comments
			.map((c: CachedComment) => ({
				comment: c,
				parsedAnnotation: parseAnnotation(c.annotation)
			}))
			.filter(
				(item): item is { comment: CachedComment; parsedAnnotation: Annotation } =>
					item.parsedAnnotation !== null
			)
	);

	// Stable key could be derived if needed; we intentionally do not use it here
	// because comment events should not trigger setup/cleanup effects.

	// Build a map of highlights per page
	let highlightsByPage = $derived.by(() => {
		const map = new SvelteMap<
			number,
			Array<{
				commentId: number;
				box: BoundingBox;
				color: string;
				key: string;
				isSelected: boolean;
			}>
		>();

		for (const { comment, parsedAnnotation } of commentsWithAnnotations) {
			for (let idx = 0; idx < parsedAnnotation.boundingBoxes.length; idx++) {
				const box = parsedAnnotation.boundingBoxes[idx];
				const pageNum = box.pageNumber;
				if (!map.has(pageNum)) {
					map.set(pageNum, []);
				}
				map.get(pageNum)!.push({
					commentId: comment.id,
					box,
					color: parsedAnnotation.color,
					key: `${comment.id}-${idx}`,
					isSelected: comment.isSelected ?? false
				});
			}
		}
		return map;
	});

	// Get whether any comment is pinned (user actively interacting)
	let pinnedComment = $derived(documentStore.pinnedComment);
	// Get whether any comment badge is hovered (not just highlight hover)
	let badgeHoveredComment = $derived(
		documentStore.comments.find((c: CachedComment) => c.isBadgeHovered)
	);

	// Track pending render timeout for cleanup
	let pendingRenderTimeout: ReturnType<typeof setTimeout> | null = null;
	let observer: MutationObserver | null = null;

	// Store event listener references for cleanup
	type HighlightElement = HTMLDivElement & {
		_listeners?: { mouseenter: () => void; mouseleave: () => void; click: () => void };
	};

	const cleanupHighlights = (container: HTMLDivElement) => {
		container.querySelectorAll<HighlightElement>('.annotation-highlight').forEach((el) => {
			// Remove event listeners before removing element
			if (el._listeners) {
				el.removeEventListener('mouseenter', el._listeners.mouseenter);
				el.removeEventListener('mouseleave', el._listeners.mouseleave);
				el.removeEventListener('click', el._listeners.click);
			}
			el.remove();
		});
	};

	// Debounced render to consolidate multiple rapid calls
	const scheduleRender = () => {
		if (pendingRenderTimeout) {
			clearTimeout(pendingRenderTimeout);
		}
		pendingRenderTimeout = setTimeout(() => {
			pendingRenderTimeout = null;
			renderHighlights();
		}, RENDER_DEBOUNCE_MS);
	};

	// Render highlights into the page elements
	const renderHighlights = () => {
		if (!viewerContainer) return;

		// Do not remove all highlights here; we'll reconcile per-page instead.

		// For each page with highlights
		for (const [pageNum, highlights] of highlightsByPage) {
			const pageElement = viewerContainer.querySelector(
				`[data-page-number="${pageNum}"]`
			) as HTMLElement | null;
			if (!pageElement) continue;

			// Check if page has finished rendering (has a canvas with dimensions)
			const canvas = pageElement.querySelector('canvas');
			if (!canvas || canvas.width === 0) continue;

			const textLayer = pageElement.querySelector('.textLayer') as HTMLElement | null;
			if (!textLayer) continue;

			// Bounding boxes are normalized to 0-1 relative to text layer
			const textLayerRect = textLayer.getBoundingClientRect();

			for (const highlight of highlights) {
				const { box, color, key, commentId, isSelected } = highlight;

				// reuse an existing element if one already exists for this key
				const existingEl = textLayer.querySelector<HighlightElement>(
					`.annotation-highlight[data-key="${key}"]`
				);
				if (existingEl) {
					// update position & visual attributes and keep event listeners
					const left = box.x * textLayerRect.width;
					const top = box.y * textLayerRect.height;
					const width = box.width * textLayerRect.width;
					const height = box.height * textLayerRect.height;
					const shouldHideOthers = !!pinnedComment || !!badgeHoveredComment;
					const isVisible = !shouldHideOthers || isSelected;

					existingEl.style.left = `${left}px`;
					existingEl.style.top = `${top}px`;
					existingEl.style.width = `${width}px`;
					existingEl.style.height = `${height}px`;
					existingEl.style.backgroundColor = color;
					existingEl.style.pointerEvents = isVisible ? 'auto' : 'none';
					existingEl.style.opacity = isVisible ? '1' : '0';
					existingEl.dataset.commentId = String(commentId);
					continue;
				}

				// Position relative to the text layer (box coordinates are 0-1 relative)
				const left = box.x * textLayerRect.width;
				const top = box.y * textLayerRect.height;
				const width = box.width * textLayerRect.width;
				const height = box.height * textLayerRect.height;

				// Determine visibility: only hide other highlights when:
				// - A comment is pinned (user clicked to keep it open), OR
				// - A badge is being hovered (not just the highlight itself)
				const shouldHideOthers = !!pinnedComment || !!badgeHoveredComment;
				const isVisible = !shouldHideOthers || isSelected;

				const div = document.createElement('div') as HighlightElement;
				div.className = 'annotation-highlight';
				div.dataset.commentId = String(commentId);
				div.dataset.key = key;

				div.style.cssText = `
					position: absolute;
					left: ${left}px;
					top: ${top}px;
					width: ${width}px;
					height: ${height}px;
					background-color: ${color};
					mix-blend-mode: multiply;
					pointer-events: ${isVisible ? 'auto' : 'none'};
					cursor: pointer;
					z-index: 5;
					border-radius: 2px;
					opacity: ${isVisible ? 1 : 0};
					transition: opacity ${OPACITY_TRANSITION_MS}ms ease-in-out;
				`;

				// Create named listener functions for cleanup
				const listeners = {
					mouseenter: () => documentStore.setHighlightHovered(commentId),
					mouseleave: () => documentStore.setHighlightHovered(null),
					click: () => {
						documentStore.setPinned(commentId);
						documentStore.setCommentCardActive(true);
						documentStore.setSelected(commentId);
					}
				};

				// Store listeners on element for later cleanup
				div._listeners = listeners;

				div.addEventListener('mouseenter', listeners.mouseenter);
				div.addEventListener('mouseleave', listeners.mouseleave);
				div.addEventListener('click', listeners.click);

				textLayer.appendChild(div);
			}

			// Remove highlights from this page that are no longer in the
			// current highlights list (per-page cleanup to avoid global teardown)
			const pageKeys = new Set(highlights.map((h) => h.key));
			textLayer.querySelectorAll<HighlightElement>('.annotation-highlight').forEach((el) => {
				const elKey = el.dataset.key;
				if (!elKey) return;
				if (!pageKeys.has(elKey)) {
					if (el._listeners) {
						el.removeEventListener('mouseenter', el._listeners.mouseenter);
						el.removeEventListener('mouseleave', el._listeners.mouseleave);
						el.removeEventListener('click', el._listeners.click);
					}
					el.remove();
				}
			});
		}
	};

	const setupObserver = () => {
		if (!viewerContainer) return;

		// Clean up existing observer
		observer?.disconnect();

		observer = new MutationObserver((mutations) => {
			// Check if any canvas was added or modified
			const shouldRerender = mutations.some((mutation) => {
				if (mutation.type === 'childList') {
					return Array.from(mutation.addedNodes).some(
						(node) =>
							node instanceof HTMLElement &&
							(node.tagName === 'CANVAS' || node.querySelector?.('canvas'))
					);
				}
				return false;
			});

			if (shouldRerender) {
				scheduleRender();
			}
		});

		observer.observe(viewerContainer, {
			childList: true,
			subtree: true
		});

		// Initial render
		scheduleRender();
	};

	// Re-render when comment content, scale, or container changes
	// Use commentsKey to avoid re-rendering on interaction state changes
	$effect(() => {
		// Dependencies - only viewer/container/scale changes should re-run setup.
		// Do NOT depend on `commentsKey` here: comment websocket events should not
		// cause the observer / effect teardown and therefore should not cause a
		// full highlight cleanup (that was causing flicker).
		void scale;

		if (viewerContainer) {
			setupObserver();

			return () => {
				// Clean up all pending operations
				if (pendingRenderTimeout) {
					clearTimeout(pendingRenderTimeout);
					pendingRenderTimeout = null;
				}
				observer?.disconnect();
				observer = null;
				// Clean up highlights when effect re-runs or component unmounts
				if (viewerContainer) {
					cleanupHighlights(viewerContainer);
				}
			};
		}
	});

	// Update highlight visibility without full re-render
	$effect(() => {
		// Dependencies - interaction state
		void pinnedComment;
		void badgeHoveredComment;

		if (!viewerContainer) return;

		// Update visibility of existing highlights
		const shouldHideOthers = !!pinnedComment || !!badgeHoveredComment;
		const selectedId = pinnedComment?.id ?? badgeHoveredComment?.id ?? null;

		viewerContainer.querySelectorAll<HTMLElement>('.annotation-highlight').forEach((el) => {
			const commentId = parseInt(el.dataset.commentId ?? '0', 10);
			const isSelected = commentId === selectedId;
			const isVisible = !shouldHideOthers || isSelected;

			el.style.opacity = isVisible ? '1' : '0';
			el.style.pointerEvents = isVisible ? 'auto' : 'none';
		});
	});

	// Schedule a re-render when the highlights content changes (structural updates
	// like new/updated/deleted comments). This deliberately does NOT tear down the
	// observer or cleanup everything — it only schedules the incremental render.
	$effect(() => {
		void highlightsByPage;
		if (viewerContainer) scheduleRender();
	});
</script>

<!-- This component renders highlights imperatively into the PDF pages -->
