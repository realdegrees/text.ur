<script lang="ts">
	import { documentStore } from '$lib/runes/document.svelte.js';
	import CommentCluster from './CommentCluster.svelte';
	import LL from '$i18n/i18n-svelte';
	import { onMount } from 'svelte';
	import { BADGE_HEIGHT_PX } from './constants';
	import type { Annotation, CommentRead } from '$api/types';
	import { SvelteMap } from 'svelte/reactivity';

	interface Props {
		viewerContainer: HTMLDivElement | null;
		scrollTop: number;
	}

	let { viewerContainer, scrollTop }: Props = $props();

	let containerElement: HTMLDivElement | null = $state(null);

	// Calculate the Y position of each comment relative to the sidebar's scroll position
	// Returns the CENTER Y position of the first highlight box
	const getCommentPosition = (comment: CommentRead): { x: number; y: number } | null => {
		if (!viewerContainer || !comment.annotation) return null;

		const firstBox = comment.annotation.boundingBoxes[0];
		if (!firstBox) return null;

		const pageElement = viewerContainer.querySelector(
			`[data-page-number="${firstBox.page_number}"]`
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
		return {
			x: firstBox.x * textLayerRect.width,
			y: yRelativeToContainer - BADGE_HEIGHT_PX / 2
		};
	};

	// Group comments by Y position proximity (clustering)
	type CommentClusterData = (CommentRead & {
		highlightPosition: { x: number; y: number };
	})[];

	// Track actual rendered heights of clusters (key is comment IDs joined)
	let clusterHeights = new SvelteMap<string, number>();

	// Helper to check if any comment in a cluster is expanded (pinned/editing/replying).
	// Hover alone no longer expands clusters — only explicit pin or interaction does.
	const isClusterExpanded = (comments: CommentRead[]): boolean => {
		return comments.some((c) => {
			const state = documentStore.comments.getState(c.id);
			return state?.isPinned || state?.isEditing || state?.isReplying;
		});
	};

	// Force update trigger for PDF page rendering
	let renderTrigger = $state(0);

	let baseClusters = $derived.by((): CommentClusterData[] => {
		// Depend on multiple signals to trigger recalculation
		void scrollTop; // When user scrolls
		void documentStore.documentScale; // When PDF is scaled
		void documentStore.numPages; // When PDF is loaded
		void renderTrigger; // When pages are rendered into DOM

		const commentPositionMap = documentStore.comments.topLevelComments
			.map((comment) => ({
				comment,
				highlightPosition: getCommentPosition(comment)
			}))
			.filter(
				(
					item
				): item is {
					comment: CommentRead & { annotation: Annotation };
					highlightPosition: { x: number; y: number };
				} => !!item.highlightPosition
			)
			.sort((a, b) => {
				return a.highlightPosition.y - b.highlightPosition.y;
			});

		if (commentPositionMap.length === 0) return [];

		const result: CommentClusterData[] = [];
		let currentCluster: CommentClusterData = [
			{
				...commentPositionMap[0].comment,
				highlightPosition: commentPositionMap[0].highlightPosition
			}
		];

		for (let i = 1; i < commentPositionMap.length; i++) {
			const item = commentPositionMap[i];
			const lastClusterY = currentCluster[0].highlightPosition.y;
			if (item.highlightPosition.y - lastClusterY <= BADGE_HEIGHT_PX) {
				// Merge into current cluster
				currentCluster.push({
					...item.comment,
					highlightPosition: item.highlightPosition
				});
				currentCluster = currentCluster.sort((a, b) => {
					return a.id - b.id;
				});
			} else {
				// Start a new cluster
				result.push(currentCluster);
				currentCluster = [
					{
						...item.comment,
						highlightPosition: item.highlightPosition
					}
				];
			}
		}

		// Don't forget the last cluster
		result.push(currentCluster);
		return result;
	});

	// Adjust cluster positions to prevent overlaps with expanded cards
	let repositionedClusters = $derived.by((): CommentClusterData[] => {
		const GAP_PX = 8; // Gap between clusters

		// Depend on clusterHeights to recalculate when heights change
		void clusterHeights;

		// Deep clone baseClusters to avoid mutating the original
		// Each cluster needs its own copy of highlightPosition
		const adjusted = baseClusters.map((cluster) =>
			cluster.map((comment) => ({
				...comment,
				highlightPosition: { ...comment.highlightPosition }
			}))
		);

		// Iteratively adjust positions from top to bottom using the clones
		for (let i = 0; i < adjusted.length; i++) {
			const current = adjusted[i];

			// Get the actual rendered height, or use badge height as fallback
			const currentIsExpanded = isClusterExpanded(current);
			const currentHeight = currentIsExpanded
				? clusterHeights.get(current[0].id.toString()) || BADGE_HEIGHT_PX
				: BADGE_HEIGHT_PX;

			const currentBottom = current[0].highlightPosition.y + currentHeight;

			// Check all clusters below and push them down if they overlap
			for (let j = i + 1; j < adjusted.length; j++) {
				const below = adjusted[j];

				// If current cluster's bottom overlaps with the cluster below, push it down
				if (currentBottom + GAP_PX > below[0].highlightPosition.y) {
					below[0].highlightPosition.y = currentBottom + GAP_PX;
				}
			}
		}

		return adjusted;
	});

	// Watch for text layer size changes to recalculate cluster positions
	onMount(() => {
		if (!viewerContainer) return;

		documentStore.commentSidebarRef = containerElement;

		// Watch for text layers being added and resized to trigger recalculation
		const textLayerObserver = new ResizeObserver(() => {
			renderTrigger++;
		});

		const mutationObserver = new MutationObserver((mutations) => {
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
				textLayerObserver.observe(layer as HTMLElement);
			});

			// Trigger a recalculation when new text layers are detected
			renderTrigger++;
		});

		mutationObserver.observe(viewerContainer, {
			childList: true,
			subtree: true
		});

		return () => {
			textLayerObserver.disconnect();
			mutationObserver.disconnect();
		};
	});
</script>

<div class="relative h-full" bind:this={containerElement}>
	{#key repositionedClusters.length}
		{#each repositionedClusters as cluster, idx (idx)}
			{@const clusterY = cluster[0].highlightPosition.y}
			<div class="absolute right-3" style="top: {clusterY}px; left: 12px;">
				<CommentCluster
					comments={cluster}
					onHeightChange={(height: number) => {
						clusterHeights.set(cluster[0].id.toString(), height);
					}}
				/>
			</div>
		{/each}
	{/key}

	{#if !repositionedClusters.length}
		<div class="flex h-full items-center justify-center p-4">
			<p class="text-center text-sm text-text/40">{$LL.comments.selectTextHint()}</p>
		</div>
	{/if}
</div>
