<script lang="ts">
	import { documentStore, type TypedComment } from '$lib/runes/document.svelte.js';
	import CommentCluster from './CommentCluster.svelte';
	import { onMount } from 'svelte';
	import { CLUSTER_THRESHOLD_PX, BADGE_HEIGHT_PX } from './constants';
	import type { Annotation } from '$types/pdf';
	import { SvelteMap } from 'svelte/reactivity';
	import { fade } from 'svelte/transition';

	interface Props {
		viewerContainer: HTMLDivElement | null;
		scrollTop: number;
	}

	let { viewerContainer, scrollTop }: Props = $props();

	let containerElement: HTMLDivElement | null = $state(null);

	// Calculate the Y position of each comment relative to the sidebar's scroll position
	// Returns the CENTER Y position of the first highlight box
	const getCommentYPosition = (comment: TypedComment): number | null => {
		if (!viewerContainer || !comment.annotation) return null;

		const firstBox = comment.annotation.boundingBoxes[0];
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
		comments: TypedComment[];
		yPosition: number;
	}

	// Update tick triggered by text layer resizes
	let clustersUpdateTick = $state(0);

	// Track actual rendered heights of clusters (key is comment IDs joined)
	let clusterHeights = new SvelteMap<string, number>();

	// Helper to check if any comment in a cluster is expanded
	const isClusterExpanded = (comments: TypedComment[]): boolean => {
		return comments.some(
			(c) => {
				const state = documentStore.comments.getState(c.id);
				return state?.isCommentHovered || state?.isHighlightHovered || state?.isPinned || state?.isEditing;
			}
		);
	};

	let baseClusters = $derived.by((): CommentClusterData[] => {
		// Depend on the update tick (triggered by ResizeObserver)
		void clustersUpdateTick;
		void scrollTop;

		const positioned = documentStore.comments.withAnnotations
			.map((comment) => ({
				comment,
				y: getCommentYPosition(comment)
			}))
			.filter(
				(item): item is { comment: TypedComment & { annotation: Annotation }; y: number } =>
					!!item.y
			)
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
		const GAP_PX = 8; // Gap between clusters

		// Iteratively adjust positions from top to bottom
		for (let i = 0; i < baseClusters.length; i++) {
			const current = baseClusters[i];
			const currentKey = current.comments.map((c) => c.id).join('-');

			// Get the actual rendered height, or use badge height as fallback
			const currentIsExpanded = isClusterExpanded(current.comments);
			const currentHeight = currentIsExpanded
				? clusterHeights.get(currentKey) || BADGE_HEIGHT_PX
				: BADGE_HEIGHT_PX;

			const currentBottom = current.yPosition + currentHeight;

			// Check all clusters below and push them down if they overlap
			for (let j = i + 1; j < baseClusters.length; j++) {
				const below = baseClusters[j];

				// If current cluster's bottom overlaps with the cluster below, push it down
				if (currentBottom + GAP_PX > below.yPosition) {
					below.yPosition = currentBottom + GAP_PX;
				}
			}
		}

		return baseClusters;
	});

	// Watch for text layer size changes to recalculate cluster positions
	onMount(() => {
		if (!viewerContainer) return;

		documentStore.commentSidebarRef = containerElement;

		// Use ResizeObserver to detect when PDF.js finishes scaling text layers
		// Wait 2 RAF to match AnnotationLayer timing
		const resizeObserver = new ResizeObserver(() => {
			clustersUpdateTick++;
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
		<div class="absolute right-3 left-3" style="top: {cluster.yPosition}px;">
			<CommentCluster
				comments={cluster.comments}
				yPosition={cluster.yPosition}
				{scrollTop}
				onHeightChange={(height: number) => {
					clusterHeights.set(clusterKey, height);
					clusterHeights = clusterHeights; // trigger reactivity
				}}
			/>
		</div>
	{/each}

	{#if !clusters.length && !documentStore.comments.withAnnotations.length}
		<div class="flex h-full items-center justify-center p-4">
			<p class="text-center text-sm text-text/40">Select text in the PDF to add a comment</p>
		</div>
	{/if}
</div>
