<script lang="ts">
	import {
		documentStore,
		type CommentState,
		type TypedComment
	} from '$lib/runes/document.svelte.js';
	import { SvelteMap } from 'svelte/reactivity';
	import CommentCard from './CommentCard.svelte';
	import ConnectionLine from './ConnectionLine.svelte';
	import CommentIcon from '~icons/material-symbols/comment-outline';
	import PinIcon from '~icons/material-symbols/push-pin';
	import PinOffIcon from '~icons/material-symbols/push-pin-outline';

	interface Props {
		comments: TypedComment[];
		adjustedY: number;
		scrollTop?: number;
		onHeightChange?: (height: number) => void;
	}

	$effect(() => {
		const pinnedComments = Array.from(states.entries()).filter(([, state]) => state?.isPinned).map(([id, state]) => ({id, ...state}));
		if (pinnedComments.length > 1) {
			// Ensure only one comment is pinned at a time in this cluster
			// If one of the pinnedComments matches the highlight hovered comment (prio1) or hovered tab comment (prio2), keep that one pinned
			const highlightHovered = pinnedComments.find((c) => c?.isHighlightHovered);
			const tabHovered = pinnedComments.find((c) => c?.isCommentHovered);

			let toKeepPinned: CommentState;
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
					documentStore.comments.setPinned(c.id, false);
				} else {
					selectedCommentId = c.id;
				}
			});
		}
	});

	let { comments, adjustedY, scrollTop, onHeightChange }: Props = $props();

	let states = $derived.by(() =>
		new SvelteMap(comments.map((c) => ([c.id, documentStore.comments.getState(c.id)])))
	);

	// Track which comment is selected in this group (defaults to first)
	let selectedCommentId = $state<number | null>(null);
	let selectedComment: TypedComment = $derived(
		comments.find((c) => c.id === selectedCommentId) ??
			comments.find((c) => states.get(c.id)?.isPinned) ??
			comments[0]
	);
	let hoveredTabComment: TypedComment | null = $state(null);
	let hoveredHighlightComment: TypedComment | null = $derived.by(() => {
		return comments.find((c) => states.get(c.id)?.isHighlightHovered) ?? null;
	});

	// ! This only checks the top level comments, replies are not included
	let anyCommentHovered = $derived(!!comments.find((c) => states.get(c.id)?.isCommentHovered));
	let anyHighlightHovered = $derived(!!comments.find((c) => states.get(c.id)?.isHighlightHovered));
	let anyCommentPinned = $derived(!!comments.find((c) => states.get(c.id)?.isPinned));
	let anyCommentEditing = $derived(!!comments.find((c) => states.get(c.id)?.isEditing));

	// Show expanded card when badge is hovered, highlight is hovered, comment is pinned, or input is active
	let showCard = $derived(
		anyCommentHovered || anyHighlightHovered || anyCommentPinned || anyCommentEditing
	);

	let commentCount = $derived(comments.length);
	let clusterRef: HTMLElement | null = $state(null);

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
			documentStore.comments.setCommentHovered(selectedComment.id, false);
		}}
		onmouseenter={() => {
			documentStore.comments.setCommentHovered(selectedComment.id, true);
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
								if (documentStore.comments.getState(selectedComment.id)?.isPinned) {
									documentStore.comments.setPinned(c.id, true);
								}
								if (documentStore.comments.getState(selectedComment.id)?.isCommentHovered) {
									documentStore.comments.setCommentHovered(selectedComment.id, false);
								}
								selectedCommentId = c.id;
							}}
							onmouseenter={() => {
								if (selectedComment === c) return;
								documentStore.comments.setCommentHovered(c.id, true);
								hoveredTabComment = c;
							}}
							onmouseleave={() => {
								if (selectedComment === c) return;
								documentStore.comments.setCommentHovered(c.id, false);
								hoveredTabComment = null;
							}}
						>
							{c.user?.username?.slice(0, 10) ?? `Comment ${idx + 1}`}
						</button>
					{/each}
				</div>

				<!-- Pin button -->
				<button
					class="text-text/60 hover:bg-text/5 hover:text-text rounded-sm p-1 transition-colors"
					onclick={(e) => {
						e.stopPropagation();
						documentStore.comments.setPinned(selectedComment.id, !documentStore.comments.getState(selectedComment.id)?.isPinned);
					}}
					title={documentStore.comments.getState(selectedComment.id)?.isPinned ? 'Unpin comment' : 'Pin comment'}
				>
					{#if documentStore.comments.getState(selectedComment.id)?.isPinned}
						<PinIcon class="text-text h-4 w-4 transition-colors hover:text-red-400" />
					{:else}
						<PinOffIcon class="hover:text-text h-4 w-4 hover:animate-bounce" />
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
					<ConnectionLine
						comment={hoveredTabComment}
						yPosition={adjustedY}
						opacity={0.7}
						{scrollTop}
					/>
				{/if}
				{#if anyCommentPinned && hoveredHighlightComment}
					<!-- Connection line for hovered tab comment -->
					<ConnectionLine
						comment={hoveredHighlightComment}
						yPosition={adjustedY}
						opacity={0.7}
						{scrollTop}
					/>
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
			documentStore.comments.setCommentHovered(selectedComment.id, true);
		}}
	>
		<div
			class="bg-inset ring-3 ring-primary/70 drop-shadow-xs flex h-8 w-8 cursor-pointer items-center justify-center rounded shadow-md shadow-black/20"
		>
			{#if commentCount > 1}
				<span class="text-text font-bold">{commentCount}</span>
			{:else}
				<CommentIcon class="text-text h-4 w-4" />
			{/if}
		</div>
	</button>
{/if}
