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
		yPosition: number;
		scrollTop?: number;
		onHeightChange?: (height: number) => void;
	}

	// ? This is needed for when a comment is pinned by clicking its highlight, then the currently active comment needs to be unpinned
	$effect(() => {
		const pinnedComments = Array.from(commentStates.values()).filter(
			(state): state is CommentState => !!state?.isPinned
		);
		if (pinnedComments.length > 1) {
			// Ensure only one comment is pinned at a time in this cluster
			// If one of the pinnedComments matches the highlight hovered comment (prio1) or hovered tab comment (prio2), keep that one pinned
			const highlightHovered = pinnedComments.find((c) => c?.isHighlightHovered);
			const tabHovered = pinnedComments.find((c) => c?.isCommentHovered);

			let toKeepPinned: CommentState | undefined;
			if (highlightHovered && pinnedComments.includes(highlightHovered)) {
				toKeepPinned = highlightHovered;
			} else if (tabHovered && pinnedComments.includes(tabHovered)) {
				toKeepPinned = tabHovered;
			} else {
				toKeepPinned = pinnedComments[0];
			}

			// Unpin all except toKeepPinned
			pinnedComments.forEach((c) => {
				if (c !== toKeepPinned && c.isPinned) {
					c.isPinned = false;
				} else if (c === toKeepPinned) {
					selectedCommentId = c.id;
				}
			});
		}
	});

	let { comments, yPosition, scrollTop, onHeightChange }: Props = $props();

	let commentStates = $derived.by(
		() => new SvelteMap(comments.map((c) => [c.id, documentStore.comments.getState(c.id)]))
	);

	// Track which comment is selected in this group (defaults to first)
	let selectedCommentId = $state<number | null>(null);

	let hoveredTabId: number | null = $state(null);
	let hoveredTabCommentState = $derived.by(() => commentStates.get(hoveredTabId ?? -1));
	let hoveredHighlightComment: TypedComment | null = $derived.by(() => {
		return comments.find((c) => commentStates.get(c.id)?.isHighlightHovered) ?? null;
	});

	let activeComment: TypedComment = $derived(
		hoveredHighlightComment ??
			comments.find((c) => c.id === selectedCommentId) ??
			comments.find((c) => commentStates.get(c.id)?.isPinned) ??
			comments[0]
	);
	let activeCommentState = $derived.by(() => commentStates.get(activeComment.id));

	// ! This only checks the top level comments, replies are not included
	let anyCommentHovered = $derived(
		!!comments.find((c) => commentStates.get(c.id)?.isCommentHovered)
	);
	let anyHighlightHovered = $derived(
		!!comments.find((c) => commentStates.get(c.id)?.isHighlightHovered)
	);
	let anyCommentPinned = $derived(!!comments.find((c) => commentStates.get(c.id)?.isPinned));
	let anyCommentEditing = $derived(!!comments.find((c) => commentStates.get(c.id)?.isEditing));

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
		data-comment-badge={activeComment?.id}
		data-badge-active="true"
		onmouseleave={() => {
			const state = commentStates.get(activeComment.id);
			if (state) state.isCommentHovered = false;
		}}
		onmouseenter={() => {
			const state = commentStates.get(activeComment.id);
			if (state) state.isCommentHovered = true;
		}}
	>
		<!-- Cluster header: tabs for multiple comments or single author header -->
		<div class="border-text/30 w-full border-b p-1.5 pb-0">
			<div class="border-text/10 pb-0! flex items-center justify-between gap-1.5 border-b">
				<div class="flex gap-1.5">
					{#each comments as c, idx (c.id)}
						{@const state = commentStates.get(c.id)}
						<button
							class="cursor-pointer rounded-t px-2 py-1.5 text-xs font-medium transition-colors flex flex-row items-center gap-1.5
							{activeComment === c
								? 'bg-inset text-text'
								: 'text-text/50 hover:bg-text/5 hover:text-text/70 hover:animate-pulse'}"
							onclick={(e) => {
								e.stopPropagation();
								if (activeComment === c && state) {
									state.isPinned = !state.isPinned;
									return;
								}
								if (state) {
									state.isCommentHovered = true;
									state.isPinned = activeCommentState?.isPinned;
								}
								if (activeCommentState) {
									activeCommentState.isPinned = false;
									activeCommentState.isCommentHovered = false;
								}

								selectedCommentId = c.id;
							}}
							onmouseenter={() => {
								hoveredTabId = c.id;
								if (state) state.isCommentHovered = true;
							}}
							onmouseleave={() => {
								hoveredTabId = null;
								if (activeComment === c) return;
								if (state) state.isCommentHovered = false;
							}}
						>
							<p>{c.user?.username?.slice(0, 10) ?? `Comment ${idx + 1}`}</p>
							{#if state?.isPinned}
								<PinIcon class="text-text h-4 w-4 transition-colors hover:text-red-400" />
							{:else if hoveredTabId === c.id && c.id === activeComment.id}
								<PinOffIcon class="hover:text-text h-4 w-4" />
							{/if}
						</button>
					{/each}
				</div>
			</div>
		</div>
		{#if activeComment}
			<CommentCard comment={activeComment} />

			{#if (anyCommentHovered || anyHighlightHovered) && (anyCommentPinned || anyCommentHovered)}
				<!-- Connection line for this card -->

				<ConnectionLine state={activeCommentState} {yPosition} {scrollTop} />

				{#if hoveredTabId !== null && hoveredTabId !== activeComment.id}
					<!-- Connection line for hovered tab comment -->
					<ConnectionLine state={hoveredTabCommentState} {yPosition} opacity={0.7} {scrollTop} />
				{/if}
			{/if}
		{/if}
	</div>
{:else}
	<!-- Compact badge - only hover on badge itself triggers expansion -->
	<button
		bind:this={clusterRef}
		class="relative z-10 inline-block"
		data-comment-badge={activeComment?.id}
		onmouseenter={() => {
			if (activeCommentState) activeCommentState.isCommentHovered = true;
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
