<script lang="ts">
	import {
		documentStore,
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

	let { comments, yPosition, scrollTop, onHeightChange }: Props = $props();

	let commentStates = $derived.by(
		() => new SvelteMap(comments.map((c) => [c.id, documentStore.comments.getState(c.id)]))
	);

	// Track which comment is selected in this group (defaults to first)
	// eslint-disable-next-line svelte/prefer-writable-derived
	let selectedTabId = $state<number | null>(null);

	let hoveredTabId: number | null = $state(null);
	let hoveredTabCommentState = $derived.by(() => commentStates.get(hoveredTabId ?? -1));
	let highlightHoveredComment: TypedComment | null = $derived.by(() => {
		return comments.find((c) => commentStates.get(c.id)?.isHighlightHovered) ?? null;
	});
	let firstCommentHovered: TypedComment | null = $derived.by(() => {
		return comments.find((c) => commentStates.get(c.id)?.isCommentHovered) ?? null;
	});
	let firstEditingComment: TypedComment | null = $derived.by(() => {
		return comments.find((c) => commentStates.get(c.id)?.isEditing) ?? null;
	});
	let firstReplyingComment: TypedComment | null = $derived.by(() => {
		return comments.find((c) => commentStates.get(c.id)?.isReplying) ?? null;
	});
	let firstPinnedComment: TypedComment | null = $derived.by(() => {
		return comments.find((c) => commentStates.get(c.id)?.isPinned) ?? null;
	});
	let selectedTabComment = $derived.by(() => {
		return comments.find((c) => c.id === selectedTabId) ?? null;
	});

	let activeComment: TypedComment = $derived(
		highlightHoveredComment ??
			firstEditingComment ??
			firstReplyingComment ??
			selectedTabComment ??
			firstPinnedComment ??
			comments[0]
	);

	$effect(() => {
		selectedTabId = activeComment.id;
	});

	let activeCommentState = $derived.by(() => commentStates.get(activeComment.id));

	// Show expanded card when badge is hovered, highlight is hovered, comment is pinned, or input is active
	let showCard = $derived(
		hoveredTabCommentState ||
			highlightHoveredComment ||
			firstPinnedComment ||
			firstEditingComment ||
			firstReplyingComment ||
			firstCommentHovered
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
		class="relative z-50 overflow-hidden rounded-lg bg-background shadow-lg ring-0 shadow-black/20 ring-primary/30 transition-all {firstPinnedComment
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
		<div class="w-full border-b border-text/30 p-1.5 pb-0">
			<div class="flex items-center justify-between gap-1.5 border-b border-text/10 pb-0!">
				<div class="flex flex-wrap items-center gap-1.5">
					{#each comments as c, idx (c.id)}
						{@const state = commentStates.get(c.id)}
						<button
							class="flex cursor-pointer flex-row items-center gap-1.5 rounded-t px-2 py-1.5 text-xs font-medium transition-colors
							{activeComment === c
								? 'bg-inset text-text'
								: 'text-text/50 hover:animate-pulse hover:bg-text/5 hover:text-text/70'}"
							onclick={(e) => {
								e.stopPropagation();
								if (activeComment === c && state) {
									state.isPinned = !state.isPinned;
									return;
								}
								if (state) {
									state.isCommentHovered = true;
									// state.isPinned = activeCommentState?.isPinned;
								}
								if (activeCommentState) {
									// activeCommentState.isPinned = false;
									activeCommentState.isCommentHovered = false;
								}

								selectedTabId = c.id;
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
								<PinIcon class="h-4 w-4 text-text transition-colors hover:text-red-400" />
							{:else if c.id === activeComment.id}
								<PinOffIcon class="h-4 w-4 hover:text-text" />
							{/if}
						</button>
					{/each}
				</div>
			</div>
		</div>
		{#if activeComment}
			<CommentCard comment={activeComment} />

			{#if hoveredTabCommentState || firstCommentHovered || highlightHoveredComment}
				<!-- Connection line for this card -->

				<ConnectionLine commentState={activeCommentState} {yPosition} {scrollTop} />

				{#if hoveredTabId !== null && hoveredTabId !== activeComment.id}
					<!-- Connection line for hovered tab comment -->
					<ConnectionLine
						commentState={hoveredTabCommentState}
						{yPosition}
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
		data-comment-badge={activeComment?.id}
		onmouseenter={() => {
			if (activeCommentState) activeCommentState.isCommentHovered = true;
		}}
	>
		<div
			class="flex h-8 w-8 cursor-pointer items-center justify-center rounded bg-inset shadow-md ring-3 shadow-black/20 ring-primary/70 drop-shadow-xs"
		>
			{#if commentCount > 1}
				<span class="font-bold text-text">{commentCount}</span>
			{:else}
				<CommentIcon class="h-4 w-4 text-text" />
			{/if}
		</div>
	</button>
{/if}
