<script lang="ts">
	import { documentStore, type CachedComment } from '$lib/runes/document.svelte.js';
	import CommentCard from './CommentCard.svelte';
	import ConnectionLine from './ConnectionLine.svelte';
	import CommentIcon from '~icons/material-symbols/comment-outline';
	import PinIcon from '~icons/material-symbols/push-pin';
	import PinOffIcon from '~icons/material-symbols/push-pin-outline';

	interface Props {
		comments: CachedComment[];
		adjustedY: number;
		scrollTop?: number;
		onHeightChange?: (height: number) => void;
	}

	$effect(() => {
		const pinnedComments = comments.filter((c) => c.isPinned);
		if (pinnedComments.length > 1) {			
			// Ensure only one comment is pinned at a time in this cluster
			// If one of the pinnedComments matches the highlight hovered comment (prio1) or hovered tab comment (prio2), keep that one pinned
			const highlightHovered = comments.find((c) => c.isHighlightHovered);
			const tabHovered = comments.find((c) => c.isCommentHovered);

			let toKeepPinned: CachedComment;
			if (highlightHovered && pinnedComments.includes(highlightHovered)) {
				toKeepPinned = highlightHovered;
			} else if (tabHovered && pinnedComments.includes(tabHovered)) {
				toKeepPinned = tabHovered;
			} else {
				toKeepPinned = pinnedComments[0];
			}

			// Unpin all except toKeepPinned
			pinnedComments.forEach((c) => {
				if (c !== toKeepPinned) {
					documentStore.setPinned(c.id, false);
				}else {
					selectedCommentId = c.id;
				}
			});
		}
	})

	let { comments, adjustedY, scrollTop, onHeightChange }: Props = $props();

	// Track which comment is selected in this group (defaults to first)
	let selectedCommentId = $state<number | null>(null);
	let selectedComment: CachedComment = $derived(
		comments.find((c) => c.id === selectedCommentId) ??
		comments.find((c) => c.isPinned) ??
		comments[0]
	);
	let hoveredTabComment: CachedComment | null = $state(null);
	let hoveredHighlightComment: CachedComment | null = $derived.by(() => {
		return comments.find((c) => c.isHighlightHovered) ?? null;
	});

	// ! This only checks the top level comments, replies are not included
	let anyCommentHovered = $derived(!!comments.find((c) => c.isCommentHovered));
	let anyHighlightHovered = $derived(!!comments.find((c) => c.isHighlightHovered));
	let anyCommentPinned = $derived(!!comments.find((c) => c.isPinned));
	let anyCommentEditing = $derived(!!comments.find((c) => c.isEditing));

	// Show expanded card when badge is hovered, highlight is hovered, comment is pinned, or input is active
	let showCard = $derived(
		anyCommentHovered || anyHighlightHovered || anyCommentPinned || anyCommentEditing
	);

	let commentCount = $derived(comments.length);
	let clusterRef: HTMLElement | null = $state(null);

	// !!! Click outside functionality is disabled in favor of a pin toggle button
	// Handle click outside to unpin comments
	// $effect(() => {
	// 	if (!anyCommentPinned) return;

	// 	const handleClickOutside = (e: MouseEvent) => {
	// 		if (clusterRef && !clusterRef.contains(e.target as Node)) {
	// 			// Unpin all comments in this cluster
	// 			comments.forEach((c) => {
	// 				if (c.isPinned) {
	// 					documentStore.setPinned(c.id, false);
	// 				}
	// 			});
	// 		}
	// 	};

	// 	// Use setTimeout to avoid the click that pinned the comment from immediately unpinning it
	// 	// Use capture phase to catch clicks before stopPropagation prevents bubbling
	// 	const timeoutId = setTimeout(() => {
	// 		document.addEventListener('click', handleClickOutside, true);
	// 	}, 0);

	// 	return () => {
	// 		clearTimeout(timeoutId);
	// 		document.removeEventListener('click', handleClickOutside, true);
	// 	};
	// });

	// Measure and report cluster height when it changes
	$effect(() => {
		if (!clusterRef || !onHeightChange) return;

		const resizeObserver = new ResizeObserver((entries) => {
			for (const entry of entries) {
				const height = entry.contentRect.height;
				onHeightChange(height);
			}
		});

		resizeObserver.observe(clusterRef);

		// Report initial height
		onHeightChange(clusterRef.offsetHeight);

		return () => {
			resizeObserver.disconnect();
		};
	});
</script>

{#if showCard}
	<!-- Expanded card - hover anywhere on card keeps it open -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		bind:this={clusterRef}
		class="bg-background ring-primary/30 relative z-50 overflow-hidden rounded-lg shadow-lg shadow-black/20 ring-0 transition-all {anyCommentPinned
			? 'ring-3'
			: ''}"
		tabindex="-1"
		data-comment-badge={selectedComment?.id}
		data-badge-active="true"
		onmouseleave={() => {
			documentStore.setCommentHovered(selectedComment.id, false);
		}}
		onmouseenter={() => {
			documentStore.setCommentHovered(selectedComment.id, true);
		}}
	>
		<!-- Cluster header: tabs for multiple comments or single author header -->
		<div class="border-text/30 w-full border-b p-1.5 pb-0">
			<div class="border-text/10 pb-0! flex items-center justify-between gap-1.5 border-b">
				<div class="flex gap-1.5">
					{#each comments as c, idx (c.id)}
						<button
							class="rounded-t px-2 py-1.5 text-xs font-medium transition-colors hover:animate-pulse
							{selectedComment === c ? 'bg-inset text-text' : 'text-text/50 hover:bg-text/5 hover:text-text/70'}"
							onclick={(e) => {
								e.stopPropagation();
								if (selectedComment === c) return;
								if (selectedComment.isPinned) {
									documentStore.setPinned(c.id, true);
								}
								if (selectedComment.isCommentHovered) {
									documentStore.setCommentHovered(selectedComment.id, false);
								}
								selectedCommentId = c.id;
							}}
							onmouseenter={() => {
								if (selectedComment === c) return;
								documentStore.setCommentHovered(c.id, true);
								hoveredTabComment = c;
							}}
							onmouseleave={() => {
								if (selectedComment === c) return;
								documentStore.setCommentHovered(c.id, false);
								hoveredTabComment = null;
							}}
						>
							{c.user?.username?.slice(0, 10) ?? `Comment ${idx + 1}`}
						</button>
					{/each}
				</div>

				<!-- Pin button -->
				<button
					class="text-text/60 hover:text-text hover:bg-text/5 rounded-sm p-1 transition-colors"
					onclick={(e) => {
						e.stopPropagation();
						documentStore.setPinned(selectedComment.id, !selectedComment.isPinned);
					}}
					title={selectedComment.isPinned ? 'Unpin comment' : 'Pin comment'}
				>
					{#if selectedComment.isPinned}
						<PinIcon class="h-4 w-4 text-text hover:text-red-400 transition-colors" />
					{:else}
						<PinOffIcon class="h-4 w-4 hover:text-text hover:animate-bounce" />
					{/if}
				</button>
			</div>
		</div>
		{#if selectedComment}
			<CommentCard comment={selectedComment} />

			{#if (anyCommentHovered && !anyHighlightHovered) || anyCommentPinned}
				<!-- Connection line for this card -->

				<ConnectionLine comment={selectedComment} yPosition={adjustedY} {scrollTop} />

				{#if hoveredTabComment}
					<!-- Connection line for hovered tab comment -->
					<ConnectionLine comment={hoveredTabComment} yPosition={adjustedY} opacity={0.7} {scrollTop} />
				{/if}
				{#if anyCommentPinned && hoveredHighlightComment}
					<!-- Connection line for hovered tab comment -->
					<ConnectionLine comment={hoveredHighlightComment} yPosition={adjustedY} opacity={0.7} {scrollTop} />
				{/if}
			{/if}
		{/if}
	</div>
{:else}
	<!-- Compact badge - only hover on badge itself triggers expansion -->
	<button
		bind:this={clusterRef}
		class="relative z-10 inline-block"
		data-comment-badge={selectedComment?.id}
		onmouseenter={() => {
			documentStore.setCommentHovered(selectedComment.id, true);
		}}
	>
		<div
			class="border-background bg-secondary drop-shadow-xs flex h-8 w-8 cursor-pointer items-center justify-center rounded-full border-2 shadow-md shadow-black/20 transition-transform hover:scale-110"
		>
			{#if commentCount > 1}
				<span class="text-text text-xs font-bold">{commentCount}</span>
			{:else}
				<CommentIcon class="text-text h-4 w-4" />
			{/if}
		</div>
	</button>
{/if}
