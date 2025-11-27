<script lang="ts">
	import { documentStore, type CachedComment } from '$lib/runes/document.svelte.js';
	import { parseAnnotation, type Annotation, type BoundingBox } from '$types/pdf';
	import { SvelteMap } from 'svelte/reactivity';
	import { OPACITY_TRANSITION_MS } from './constants';
	import { onMount } from 'svelte';

	let { viewerContainer }: { viewerContainer: HTMLElement } = $props();

	// Apply local filters to comments
	let filteredComments = $derived.by(() => {
		let result = documentStore.comments;

		// Build include/exclude sets from the store's authorFilterStates
		const states = documentStore.authorFilterStates;
		const included = new Set<number>(
			[...states.entries()].filter(([, v]) => v === 'include').map(([k]) => k)
		);
		const excluded = new Set<number>(
			[...states.entries()].filter(([, v]) => v === 'exclude').map(([k]) => k)
		);

		if (included.size > 0) {
			result = result.filter((c: CachedComment) => c.user?.id && included.has(c.user.id));
		} else if (excluded.size > 0) {
			result = result.filter((c: CachedComment) => !(c.user?.id && excluded.has(c.user.id)));
		}

		return result;
	});

	// Get comments with valid parsed annotations from the store
	// Only track annotation data, not interaction state (to avoid re-rendering on hover)
	let commentsWithAnnotations = $derived(
		filteredComments
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
				comment: CachedComment;
				box: BoundingBox;
				annotation: Annotation;
				key: string;
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
					comment,
					box,
					annotation: parsedAnnotation,
					key: `${comment.id}-${idx}`
				});
			}
		}
		return map;
	});

	// Store event listener references for cleanup
	type HighlightElement = HTMLDivElement & {
		_listeners?: { mouseenter: () => void; mouseleave: () => void; click: () => void };
	};

	// Render highlights into the page elements
	const renderHighlights = () => {
		if (!viewerContainer) return;

		const isAnyPinned = documentStore.pinnedComments.size > 0;

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

			if (textLayerRect.width === 0 || textLayerRect.height === 0) continue;
			for (const highlight of highlights) {
				const { box, annotation, key, comment } = highlight;

				const left = box.x * textLayerRect.width;
				const top = box.y * textLayerRect.height;
				const width = box.width * textLayerRect.width;
				const height = box.height * textLayerRect.height;
				const isVisible = !isAnyPinned || comment.isPinned || comment.isCommentHovered;

				// reuse an existing element if one already exists for this key
				const existingEl = textLayer.querySelector<HighlightElement>(
					`.annotation-highlight[data-key="${key}"]`
				);
				if (existingEl) {
					// update position & visual attributes and keep event listeners
					existingEl.style.left = `${left}px`;
					existingEl.style.top = `${top}px`;
					existingEl.style.width = `${width}px`;
					existingEl.style.height = `${height}px`;
					existingEl.style.backgroundColor = annotation.color;
					existingEl.style.pointerEvents = 'auto';
					existingEl.style.opacity = isVisible ? '1' : '0.4';
					existingEl.dataset.commentId = String(comment.id);
					continue;
				}

				const div = document.createElement('div') as HighlightElement;
				documentStore.addCommentHighlight(comment.id, div);
				div.className = 'annotation-highlight';
				div.dataset.commentId = String(comment.id);
				div.dataset.key = key;

				div.style.cssText = `
					position: absolute;
					left: ${left}px;
					top: ${top}px;
					width: ${width}px;
					height: ${height}px;
					background-color: ${annotation.color};
					mix-blend-mode: multiply;
					pointer-events: auto;
					cursor: pointer;
					z-index: 5;
					border-radius: 2px;
					opacity: ${isVisible ? 1 : 0.4};
					transition: opacity ${OPACITY_TRANSITION_MS}ms ease-in-out;
				`;

				// Create named listener functions for cleanup
				const listeners = {
					mouseenter: () => documentStore.setHighlightHovered(comment.id, true),
					mouseleave: () => documentStore.setHighlightHovered(comment.id, false),
					click: () => {
						documentStore.setPinned(comment.id, !comment.isPinned);
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
					documentStore.removeCommentHighlight(parseInt(el.dataset.commentId ?? '0'), el);
					el.remove();
				}
			});
		}
	};

	// Track text layers with ResizeObserver to detect when PDF.js finishes scaling
	let textLayerObserver: ResizeObserver | null = null;
	let mutationObserver: MutationObserver | null = null;

	onMount(() => {
		requestAnimationFrame(() => {
			renderHighlights();
		});

		// Observe text layer size changes to re-render when PDF.js scales
		textLayerObserver = new ResizeObserver(() => {
			requestAnimationFrame(() => {
				requestAnimationFrame(() => {
					renderHighlights();
				});
			});
		});

		// Watch for text layers being added to the DOM by PDF.js
		if (viewerContainer) {
			mutationObserver = new MutationObserver((mutations) => {
				if (!viewerContainer) return;

				// Check if any text layers were added
				let hasNewTextLayers = false;
				for (const mutation of mutations) {
					for (const node of mutation.addedNodes) {
						if (node instanceof HTMLElement) {
							if (node.classList.contains('textLayer') || node.querySelector('.textLayer')) {
								hasNewTextLayers = true;
								break;
							}
						}
					}
					if (hasNewTextLayers) break;
				}

				if (!hasNewTextLayers) return;

				// Observe new text layers with ResizeObserver
				const textLayers = viewerContainer.querySelectorAll('.textLayer');
				textLayers.forEach((layer) => {
					textLayerObserver?.observe(layer as HTMLElement);
				});

				// Trigger a render when new text layers are detected
				requestAnimationFrame(() => {
					requestAnimationFrame(() => {
						renderHighlights();
					});
				});
			});

			mutationObserver.observe(viewerContainer, {
				childList: true,
				subtree: true
			});
		}

		return () => {
			textLayerObserver?.disconnect();
			mutationObserver?.disconnect();
		};
	});

	// Schedule a re-render when the highlights content changes (structural updates
	// like new/updated/deleted comments). This deliberately does NOT tear down the
	// observer or cleanup everything — it only schedules the incremental render.
	$effect(() => {
		void highlightsByPage;
		void documentStore.documentScale;

		if (!viewerContainer) return;

		// Observe all text layers for resize
		const textLayers = viewerContainer.querySelectorAll('.textLayer');
		textLayers.forEach((layer) => {
			textLayerObserver?.observe(layer as HTMLElement);
		});

		requestAnimationFrame(() => {
			requestAnimationFrame(() => {
				renderHighlights();
			});
		});
	});
</script>

<!-- This component renders highlights imperatively into the PDF pages -->
