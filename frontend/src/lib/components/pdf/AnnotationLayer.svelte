<script lang="ts">
	import {
		documentStore,
		type CommentState,
		type TypedComment
	} from '$lib/runes/document.svelte.js';
	import { type Annotation, type BoundingBox } from '$types/pdf';
	import { SvelteMap } from 'svelte/reactivity';
	import { OPACITY_TRANSITION_MS } from './constants';
	import { onMount } from 'svelte';
	import { preciseHover } from '$lib/actions/preciseHover';
	import { longPress } from '$lib/actions/longPress';
	import { hasHoverCapability } from '$lib/util/responsive.svelte';

	let { viewerContainer }: { viewerContainer: HTMLElement } = $props();

	const hexToRgba = (hex: string, alpha: number = 0.3): string => {
		const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
		if (!result) return `rgba(255, 255, 0, ${alpha})`;
		const r = parseInt(result[1], 16);
		const g = parseInt(result[2], 16);
		const b = parseInt(result[3], 16);
		return `rgba(${r}, ${g}, ${b}, ${alpha})`;
	};

	// Build a map of highlights per page
	let highlightsByPage = $derived.by(() => {
		const map = new SvelteMap<
			number,
			Array<{
				comment: TypedComment;
				box: BoundingBox;
				annotation: Annotation;
				state: CommentState;
				key: string;
				color: string;
			}>
		>();

		// Initialize map with all pages as keys and empty arrays as values
		for (let pageNum = 1; pageNum <= documentStore.numPages; pageNum++) {
			map.set(pageNum, []);
		}

		for (const comment of documentStore.comments.topLevelComments) {
			if (!comment.annotation?.boundingBoxes) continue;

			// Use first tag's color if available, otherwise fall back to annotation color
			const highlightColor =
				comment.tags && comment.tags.length > 0 ? comment.tags[0].color : comment.annotation.color;

			for (let idx = 0; idx < comment.annotation.boundingBoxes.length; idx++) {
				const box = comment.annotation.boundingBoxes[idx];
				const pageNum = box.pageNumber;
				const state = documentStore.comments.getState(comment.id);
				if (state) {
					map.set(pageNum, [
						...(map.get(pageNum) ?? []),
						{
							comment,
							box,
							state,
							annotation: comment.annotation,
							key: `${comment.id}-${idx}`,
							color: hexToRgba(highlightColor)
						}
					]);
				}
			}
		}
		return map;
	});

	// Store action destroy function for cleanup
	type HighlightElement = HTMLDivElement & {
		_actionDestroy: (() => void)[];
		_clickListener?: () => void;
		_contextMenuListener?: (e: Event) => void;
	};

	// Render highlights into the page elements
	const renderHighlights = () => {
		if (!viewerContainer) return;

		const isAnyCommentHovered = documentStore.comments.commentHovered.size > 0;

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
				const { box, key, comment, state, color } = highlight;

				const left = box.x * textLayerRect.width;
				const top = box.y * textLayerRect.height;
				const width = box.width * textLayerRect.width;
				const height = box.height * textLayerRect.height;
				const isVisible = !isAnyCommentHovered || !!state?.isPinned || !!state?.isCommentHovered;

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
					existingEl.style.backgroundColor = color;
					existingEl.style.pointerEvents = 'auto';
					existingEl.style.opacity = isVisible ? '1' : '0.4';
					existingEl.dataset.commentId = String(comment.id);
					// If the contextmenu listener wasn't present (e.g., element was created
					// before this code change), attach a preventer to avoid long-press
					// opening the browser's context menu on mobile devices.
					if (!existingEl._contextMenuListener) {
						const ctxListener = (e: Event) => {
							e.preventDefault();
							e.stopPropagation();
						};
						existingEl._contextMenuListener = ctxListener;
						existingEl.addEventListener('contextmenu', ctxListener);
					}
					continue;
				}

				const div = document.createElement('div') as HighlightElement;
				div._actionDestroy = [];
				state.highlightElements = [...(state.highlightElements || []), div];
				div.className = 'annotation-highlight';
				div.dataset.commentId = String(comment.id);
				div.dataset.key = key;

				div.style.cssText = `
					position: absolute;
					left: ${left}px;
					top: ${top}px;
					width: ${width}px;
					height: ${height}px;
					background-color: ${color};
					mix-blend-mode: multiply;
					pointer-events: auto;
					cursor: pointer;
					z-index: 5;
					border-radius: 2px;
					opacity: ${isVisible ? 1 : 0.4};
					transition: opacity ${OPACITY_TRANSITION_MS}ms ease-in-out;
				`;
				// Improve touch behavior on iOS/Android: disable text/image callouts
				div.style.setProperty('-webkit-touch-callout', 'none');
				div.style.setProperty('-webkit-user-select', 'none');
				div.style.setProperty('-ms-user-select', 'none');
				div.style.setProperty('user-select', 'none');

					const isTouchDevice = !hasHoverCapability();

				// Desktop: Use hover for connection line, click to pin
				const hoverAction = preciseHover(div, {
					onEnter: () => documentStore.setHighlightHoveredDebounced(comment.id, true),
					onLeave: () => documentStore.setHighlightHoveredDebounced(comment.id, false)
				});

				// Mobile: Use long press to show connection line
				const longPressAction = longPress(div, {
					onLongPress: () => {
						if (isTouchDevice) {
							// Set active and show connection line on long press start
							documentStore.activeCommentId = comment.id;
							documentStore.longPressCommentId = comment.id;
						}
					},
					onRelease: () => {
						if (isTouchDevice) {
							// Clear long press state
							documentStore.longPressCommentId = null;
						}
					},
					duration: 500
				});

				// Store action destroy function for cleanup
				div._actionDestroy.push(longPressAction.destroy);
				div._actionDestroy.push(hoverAction.destroy);

				// Add click listener
				const clickListener = () => {
					if (isTouchDevice) {
						// Mobile: Set as active comment (will trigger scrolling)
						documentStore.activeCommentId = comment.id;
					} else {
						// Desktop: Pin/unpin
						state.isPinned = !state.isPinned;
					}
				};
				div._clickListener = clickListener;
				div.addEventListener('click', clickListener);

					// Prevent the context menu from appearing on long-press
					const contextMenuListener = (e: Event) => {
						e.preventDefault();
						e.stopPropagation();
					};
					div._contextMenuListener = contextMenuListener;
					div.addEventListener('contextmenu', contextMenuListener);
		

				textLayer.appendChild(div);
			}

			// Remove highlights from this page that are no longer in the
			// current highlights list (per-page cleanup to avoid global teardown)
			const pageKeys = new Set(highlights.map((h) => h.key));
			textLayer.querySelectorAll<HighlightElement>('.annotation-highlight').forEach((el) => {
				const elKey = el.dataset.key;
				if (!elKey) return;
				if (!pageKeys.has(elKey)) {
					// Clean up preciseHover action
					for (const actionDestroy of el._actionDestroy) {
						actionDestroy();
					}
					// Clean up click listener
					if (el._clickListener) {
						el.removeEventListener('click', el._clickListener);
					}
					if (el._contextMenuListener) {
						el.removeEventListener('contextmenu', el._contextMenuListener);
					}
					const commentState = documentStore.comments.getState(
						parseInt(el.dataset.commentId ?? '-1')
					);
					if (commentState) {
						commentState.highlightElements = commentState.highlightElements?.filter(
							(he) => he !== el
						);
					}
					el.remove();
				}
			});
		}
	};

	// Track text layers with ResizeObserver to detect when PDF.js finishes scaling
	let textLayerObserver: ResizeObserver | null = null;
	let mutationObserver: MutationObserver | null = null;

	onMount(() => {
		// Clear all existing highlight element references from comment states
		documentStore.clearHighlightReferences();

		// Observe text layer size changes to re-render when PDF.js scales
		textLayerObserver = new ResizeObserver(renderHighlights);

		// Watch for text layers being added to the DOM by PDF.js
		if (viewerContainer) {
			mutationObserver = new MutationObserver((mutations) => {
				if (!viewerContainer) return;

				// Check if any text layers were added
				let hasNewTextLayers = false;
				for (const mutation of mutations) {
					for (const node of mutation.addedNodes) {
						if (node instanceof HTMLElement) {
							if (node.classList.contains('textLayer')) {
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
				renderHighlights();
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
		renderHighlights();
	});
</script>

<!-- This component renders highlights imperatively into the PDF pages -->
