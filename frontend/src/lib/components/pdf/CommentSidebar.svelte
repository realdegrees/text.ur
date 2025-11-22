<script lang="ts">
	import { documentStore, type CachedComment } from '$lib/runes/document.svelte.js';
	import { parseAnnotation, type Annotation } from '$types/pdf';
	import CommentBadge from './CommentBadge.svelte';
	import { onMount } from 'svelte';

	interface Props {
		viewerContainer: HTMLDivElement | null;
		scale: number;
		scrollTop: number;
	}

	let { viewerContainer, scale, scrollTop }: Props = $props();

	// Clustering threshold in pixels - comments within this distance get merged
	const CLUSTER_THRESHOLD = 60;
	// Badge height for centering calculation
	const BADGE_HEIGHT = 32;

	// Force recalculation trigger
	let renderTick = $state(0);

	// Comment with parsed annotation
	interface CommentWithAnnotation extends CachedComment {
		parsedAnnotation: Annotation;
	}

	// Get comments with valid annotations
	let commentsWithAnnotations = $derived(
		documentStore.comments
			.map(c => ({ ...c, parsedAnnotation: parseAnnotation(c.annotation) }))
			.filter((c): c is CommentWithAnnotation => c.parsedAnnotation !== null)
	);

	// Calculate the Y position of each comment relative to the sidebar's scroll position
	// Returns the CENTER Y position of the first highlight box
	const getCommentYPosition = (comment: CommentWithAnnotation): number | null => {
		if (!viewerContainer) return null;

		const annotation = comment.parsedAnnotation;
		const firstBox = annotation.boundingBoxes[0];
		if (!firstBox) return null;

		const pageElement = viewerContainer.querySelector(
			`[data-page-number="${firstBox.pageNumber}"]`
		) as HTMLElement | null;
		if (!pageElement) return null;

		const canvas = pageElement.querySelector('canvas');
		if (!canvas || canvas.width === 0) return null;

		const textLayer = pageElement.querySelector('.textLayer') as HTMLElement | null;
		if (!textLayer) return null;

		// Get positions relative to the viewport
		// Use textLayerRect since bounding boxes are normalized relative to text layer
		const textLayerRect = textLayer.getBoundingClientRect();
		const containerRect = viewerContainer.getBoundingClientRect();

		// Calculate the CENTER of the annotation box
		const annotationTopInTextLayer = firstBox.y * textLayerRect.height;
		const annotationHeight = firstBox.height * textLayerRect.height;
		const annotationCenterY = annotationTopInTextLayer + (annotationHeight / 2);

		// Position relative to container viewport
		const annotationCenterInViewport = textLayerRect.top + annotationCenterY;
		const yRelativeToContainer = annotationCenterInViewport - containerRect.top;

		// Offset by half badge height to center the badge
		return yRelativeToContainer - (BADGE_HEIGHT / 2);
	};

	// Group comments by Y position proximity (clustering)
	interface CommentCluster {
		comments: CommentWithAnnotation[];
		yPosition: number;
	}

	let clusters = $derived.by((): CommentCluster[] => {
		// Dependencies for recalculation
		void scale;
		void scrollTop;
		void renderTick;

		const positioned = commentsWithAnnotations
			.map(comment => ({
				comment,
				y: getCommentYPosition(comment)
			}))
			.filter((item): item is { comment: CommentWithAnnotation; y: number } =>
				item.y !== null
			)
			.sort((a, b) => a.y - b.y);

		if (positioned.length === 0) return [];

		const result: CommentCluster[] = [];
		let currentCluster: CommentCluster = {
			comments: [positioned[0].comment],
			yPosition: positioned[0].y
		};

		for (let i = 1; i < positioned.length; i++) {
			const item = positioned[i];
			const lastClusterY = currentCluster.yPosition;

			if (item.y - lastClusterY <= CLUSTER_THRESHOLD) {
				// Merge into current cluster
				currentCluster.comments.push(item.comment);
			} else {
				// Start a new cluster
				result.push(currentCluster);
				currentCluster = {
					comments: [item.comment],
					yPosition: item.y
				};
			}
		}

		// Don't forget the last cluster
		result.push(currentCluster);

		return result;
	});

	// Watch for PDF pages being rendered
	onMount(() => {
		if (!viewerContainer) return;

		const observer = new MutationObserver(() => {
			// Trigger recalculation when DOM changes (pages rendered)
			renderTick++;
		});

		observer.observe(viewerContainer, {
			childList: true,
			subtree: true
		});

		// Initial render after a delay to let PDF.js finish
		const timeout = setTimeout(() => {
			renderTick++;
		}, 200);

		return () => {
			observer.disconnect();
			clearTimeout(timeout);
		};
	});
</script>

<div class="relative h-full">
	{#each clusters as cluster (cluster.comments.map(c => c.id).join('-'))}
		<div
			class="absolute left-3 right-3 transition-transform duration-75"
			style="top: {cluster.yPosition}px;"
		>
			<CommentBadge comments={cluster.comments} />
		</div>
	{/each}

	{#if clusters.length === 0 && commentsWithAnnotations.length === 0}
		<div class="flex h-full items-center justify-center p-4">
			<p class="text-center text-sm text-text/40">
				Select text in the PDF to add a comment
			</p>
		</div>
	{/if}
</div>
