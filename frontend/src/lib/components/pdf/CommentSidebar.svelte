<script lang="ts">
	import { documentStore, type CachedComment } from '$lib/runes/document.svelte.js';
	import { parseAnnotation, type Annotation } from '$types/pdf';
	import CommentCluster from './CommentCluster.svelte';
	import { onMount } from 'svelte';
	import { CLUSTER_THRESHOLD_PX, BADGE_HEIGHT_PX } from './constants';

	interface Props {
		viewerContainer: HTMLDivElement | null;
		scrollTop: number;
	}

	let { viewerContainer, scrollTop }: Props = $props();

	let containerElement: HTMLDivElement | null = $state(null);

	// Comment with parsed annotation
	interface CommentWithAnnotation extends CachedComment {
		parsedAnnotation: Annotation;
	}

	// Apply local filters to comments
	let filteredComments = $derived.by(() => {
		let result = documentStore.comments;

		// Filter by author filter states (include/exclude/none)
		const states = documentStore.authorFilterStates;
		const included = new Set<number>(
			[...states.entries()].filter(([, v]) => v === 'include').map(([k]) => k)
		);
		const excluded = new Set<number>(
			[...states.entries()].filter(([, v]) => v === 'exclude').map(([k]) => k)
		);

		// If there are include filters, show only those authors. Otherwise, if exclude filters exist, hide those authors.
		if (included.size > 0) {
			result = result.filter((c: CachedComment) => c.user?.id && included.has(c.user.id));
		} else if (excluded.size > 0) {
			result = result.filter((c: CachedComment) => !(c.user?.id && excluded.has(c.user.id)));
		}

		return result;
	});

	// Get comments with valid annotations
	let commentsWithAnnotations = $derived(
		filteredComments
			.map((c) => ({ ...c, parsedAnnotation: parseAnnotation(c.annotation) }))
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

		if (textLayerRect.width === 0 || textLayerRect.height === 0) return null;

		// Calculate the CENTER of the annotation box
		const annotationTopInTextLayer = firstBox.y * textLayerRect.height;
		const annotationHeight = firstBox.height * textLayerRect.height;
		const annotationCenterY = annotationTopInTextLayer + annotationHeight / 2;

		// Position relative to container viewport
		const annotationCenterInViewport = textLayerRect.top + annotationCenterY;
		const yRelativeToContainer = annotationCenterInViewport - containerRect.top;

		// Offset by half badge height to center the badge
		return yRelativeToContainer - BADGE_HEIGHT_PX / 2;
	};

	// Group comments by Y position proximity (clustering)
	interface CommentClusterData {
		comments: CommentWithAnnotation[];
		yPosition: number;
		adjustedY?: number; // Adjusted Y position to prevent overlaps with expanded cards
	}

	// Update tick triggered by text layer resizes
	let clustersUpdateTick = $state(0);

	// Track actual rendered heights of clusters (key is comment IDs joined)
	let clusterHeights = $state(new Map<string, number>());

	// Helper to check if any comment in a cluster is expanded
	const isClusterExpanded = (comments: CachedComment[]): boolean => {
		return comments.some(
			(c) => c.isCommentHovered || c.isHighlightHovered || c.isPinned || c.isEditing
		);
	};

	let baseClusters = $derived.by((): CommentClusterData[] => {
		// Depend on the update tick (triggered by ResizeObserver)
		void clustersUpdateTick;
		void scrollTop;

		const positioned = commentsWithAnnotations
			.map((comment) => ({
				comment,
				y: getCommentYPosition(comment)
			}))
			.filter((item): item is { comment: CommentWithAnnotation; y: number } => item.y !== null)
			.sort((a, b) => a.y - b.y);

		if (positioned.length === 0) return [];

		const result: CommentClusterData[] = [];
		let currentCluster: CommentClusterData = {
			comments: [positioned[0].comment],
			yPosition: positioned[0].y
		};

		for (let i = 1; i < positioned.length; i++) {
			const item = positioned[i];
			const lastClusterY = currentCluster.yPosition;

			if (item.y - lastClusterY <= CLUSTER_THRESHOLD_PX) {
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

	// Adjust cluster positions to prevent overlaps with expanded cards
	let clusters = $derived.by((): CommentClusterData[] => {
		const adjusted = baseClusters.map((cluster) => ({
			...cluster,
			adjustedY: cluster.yPosition
		}));

		const GAP_PX = 8; // Gap between clusters

		// Iteratively adjust positions from top to bottom
		for (let i = 0; i < adjusted.length; i++) {
			const current = adjusted[i];
			const currentKey = current.comments.map((c) => c.id).join('-');

			// Get the actual rendered height, or use badge height as fallback
			const currentIsExpanded = isClusterExpanded(current.comments);
			const currentHeight = currentIsExpanded
				? clusterHeights.get(currentKey) || BADGE_HEIGHT_PX
				: BADGE_HEIGHT_PX;

			const currentBottom = current.adjustedY! + currentHeight;

			// Check all clusters below and push them down if they overlap
			for (let j = i + 1; j < adjusted.length; j++) {
				const below = adjusted[j];

				// If current cluster's bottom overlaps with the cluster below, push it down
				if (currentBottom + GAP_PX > below.adjustedY!) {
					below.adjustedY = currentBottom + GAP_PX;
				}
			}
		}

		return adjusted;
	});

	// Watch for text layer size changes to recalculate cluster positions
	onMount(() => {
		if (!viewerContainer) return;

		documentStore.setCommentSidebarRef(containerElement);

		// Use ResizeObserver to detect when PDF.js finishes scaling text layers
		// Wait 2 RAF to match AnnotationLayer timing
		const resizeObserver = new ResizeObserver(() => {
			requestAnimationFrame(() => {
				requestAnimationFrame(() => {
					clustersUpdateTick++;
				});
			});
		});

		// Observe all existing text layers
		const textLayers = viewerContainer.querySelectorAll('.textLayer');
		textLayers.forEach((layer) => resizeObserver.observe(layer as HTMLElement));

		// MutationObserver to detect new pages/text layers being added
		const mutationObserver = new MutationObserver(() => {
			const newTextLayers = viewerContainer.querySelectorAll('.textLayer');
			newTextLayers.forEach((layer) => {
				// ResizeObserver is safe to call multiple times on same element
				resizeObserver.observe(layer as HTMLElement);
			});
			requestAnimationFrame(() => {
				requestAnimationFrame(() => {
					clustersUpdateTick++;
				});
			});
		});

		mutationObserver.observe(viewerContainer, {
			childList: true,
			subtree: true
		});

		// Initial calculation
		clustersUpdateTick++;

		return () => {
			resizeObserver.disconnect();
			mutationObserver.disconnect();
		};
	});
</script>

<div class="relative h-full" bind:this={containerElement}>
	{#each clusters as cluster (cluster.comments.map((c) => c.id).join('-'))}
		{@const clusterKey = cluster.comments.map((c) => c.id).join('-')}
		<div class="absolute right-3 left-3" style="top: {cluster.adjustedY ?? cluster.yPosition}px;">
			<CommentCluster
				comments={cluster.comments}
				adjustedY={cluster.adjustedY ?? cluster.yPosition}
				{scrollTop}
				onHeightChange={(height: number) => {
					clusterHeights.set(clusterKey, height);
					clusterHeights = clusterHeights; // trigger reactivity
				}}
			/>
		</div>
	{/each}

	{#if clusters.length === 0 && commentsWithAnnotations.length === 0}
		<div class="flex h-full items-center justify-center p-4">
			<p class="text-center text-sm text-text/40">Select text in the PDF to add a comment</p>
		</div>
	{/if}
</div>
