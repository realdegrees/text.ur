<script lang="ts">
	import { documentStore } from '$lib/runes/document.svelte.js';
	import { parseAnnotation, type BoundingBox } from '$types/pdf';
	import { SvelteMap } from 'svelte/reactivity';

	interface Props {
		viewerContainer: HTMLDivElement | null;
		scale: number;
	}

	let { viewerContainer, scale }: Props = $props();

	// Get comments with valid parsed annotations from the store
	let commentsWithAnnotations = $derived(
		documentStore.comments
			.map(c => ({
				comment: c,
				parsedAnnotation: parseAnnotation(c.annotation)
			}))
			.filter((c): c is { comment: typeof c.comment; parsedAnnotation: NonNullable<typeof c.parsedAnnotation> } =>
				c.parsedAnnotation !== null
			)
	);

	// Build a map of highlights per page
	let highlightsByPage = $derived.by(() => {
		const map = new SvelteMap<number, Array<{ commentId: number; box: BoundingBox; color: string; key: string; isSelected: boolean }>>();

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

	// Get whether any comment card is active
	let isCommentCardActive = $derived(documentStore.isCommentCardActive);
	let hasSelectedComment = $derived(documentStore.selectedComment !== undefined);

	// Render highlights into the page elements
	const renderHighlights = () => {
		if (!viewerContainer) return;

		// Remove existing highlights
		viewerContainer.querySelectorAll('.annotation-highlight').forEach(el => el.remove());

		// For each page with highlights
		for (const [pageNum, highlights] of highlightsByPage) {
			const pageElement = viewerContainer.querySelector(`[data-page-number="${pageNum}"]`) as HTMLElement | null;
			if (!pageElement) continue;

			// Check if page has finished rendering (has a canvas with dimensions)
			const canvas = pageElement.querySelector('canvas');
			if (!canvas || canvas.width === 0) continue;

			const textLayer = pageElement.querySelector('.textLayer') as HTMLElement | null;
			if (!textLayer) continue;

			// Bounding boxes are normalized to 0-1 relative to text layer
			// We'll append highlights to the text layer so they align perfectly
			const textLayerRect = textLayer.getBoundingClientRect();

			for (const highlight of highlights) {
				const { box, color, key, commentId, isSelected } = highlight;

				const div = document.createElement('div');
				div.className = 'annotation-highlight';
				div.dataset.commentId = String(commentId);
				div.dataset.key = key;

				// Position relative to the text layer
				// box coordinates are 0-1 relative to text layer
				const left = box.x * textLayerRect.width;
				const top = box.y * textLayerRect.height;
				const width = box.width * textLayerRect.width;
				const height = box.height * textLayerRect.height;

				// Determine visibility: only hide other highlights when actively interacting with comment card
				const shouldHideOthers = isCommentCardActive && hasSelectedComment;
				const isVisible = !shouldHideOthers || isSelected;

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
					transition: opacity 0.5s ease-in-out;
				`;

				div.addEventListener('mouseenter', () => {
					documentStore.setHighlightHovered(commentId);
				});
				div.addEventListener('mouseleave', () => {
					documentStore.setHighlightHovered(null);
				});
				div.addEventListener('click', () => {
					// Pin and select the comment when highlight is clicked
					documentStore.setPinned(commentId);
					documentStore.setCommentCardActive(true);
					documentStore.setSelected(commentId);
				});

				// Append to text layer so it inherits the same coordinate space
				textLayer.appendChild(div);
			}
		}
	};

	// Watch for pages being rendered by observing DOM changes
	let observer: MutationObserver | null = null;

	const setupObserver = () => {
		if (!viewerContainer) return;

		// Clean up existing observer
		observer?.disconnect();

		observer = new MutationObserver((mutations) => {
			// Check if any canvas was added or modified
			const shouldRerender = mutations.some(mutation => {
				if (mutation.type === 'childList') {
					return Array.from(mutation.addedNodes).some(
						node => node instanceof HTMLElement &&
						(node.tagName === 'CANVAS' || node.querySelector?.('canvas'))
					);
				}
				return false;
			});

			if (shouldRerender) {
				// Delay to let PDF.js finish
				setTimeout(renderHighlights, 100);
			}
		});

		observer.observe(viewerContainer, {
			childList: true,
			subtree: true
		});

		// Initial render attempt with delay
		setTimeout(renderHighlights, 200);
	};

	// Re-render when comments, scale, or container changes
	$effect(() => {
		// Dependencies
		void commentsWithAnnotations;
		void scale;
		void hasSelectedComment;
		void isCommentCardActive;

		if (viewerContainer) {
			setupObserver();
			// Also render after a delay for scale changes
			const timeout = setTimeout(renderHighlights, 150);
			return () => {
				clearTimeout(timeout);
				observer?.disconnect();
			};
		}
	});
</script>

<!-- This component renders highlights imperatively into the PDF pages -->
