<script lang="ts">
	import { documentStore, type TypedComment } from '$lib/runes/document.svelte.js';
	import { SvelteMap } from 'svelte/reactivity';
	import CommentCard from './CommentCard.svelte';
	import ConnectionLine from './ConnectionLine.svelte';
	import CommentIcon from '~icons/material-symbols/comment-outline';
	import PinIcon from '~icons/material-symbols/push-pin';
	import PinOffIcon from '~icons/material-symbols/push-pin-outline';
	import type { UserRead } from '$api/types';
	import { preciseHover } from '$lib/actions/preciseHover';

	interface Props {
		comments: TypedComment[];
		yPosition: number;
		scrollTop?: number;
		onHeightChange?: (height: number) => void;
	}

	let { comments, yPosition, scrollTop, onHeightChange }: Props = $props();

	let authorsInCluster = $derived.by(() => {
		const authorSet = new SvelteMap<number, UserRead>();
		for (const comment of comments) {
			if (comment.user?.id) {
				authorSet.set(comment.user.id, comment.user);
			}
		}
		return Array.from(authorSet.values());
	});

	let commentStates = $derived.by(
		() => new SvelteMap(comments.map((c) => [c.id, documentStore.comments.getState(c.id)]))
	);

	// Track which comment is selected in this group (defaults to first)

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

	// $effect(() => {
	// 	selectedTabId = activeComment.id;
	// });

	let activeCommentState = $derived.by(() => commentStates.get(activeComment.id));

	// Show expanded card when badge is hovered, highlight is hovered, comment is pinned, or input is active
	let showCard = $derived(
		hoveredTabCommentState ||
			firstPinnedComment ||
			firstEditingComment ||
			firstReplyingComment ||
			firstCommentHovered
	);

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

<div
	tabindex="-1"
	use:preciseHover={{
		onEnter: () => {
			documentStore.setCommentHoveredDebounced(activeComment.id, true);
		},
		onLeave: () => {
			for (const comment of comments) {
			documentStore.setCommentHoveredDebounced(comment.id, false);
		}
		}
	}}
	data-comment-badge={activeComment?.id}
	data-badge-active="true"
	class="{showCard ? 'w-full' : 'w-fit'}"
>
	{#if showCard}
		<!-- Expanded card - hover anywhere on card keeps it open -->
		<div
			bind:this={clusterRef}
			class="bg-background ring-3 relative z-50 overflow-hidden rounded shadow-lg shadow-black/20 transition-all {firstPinnedComment
				? 'ring-primary/70'
				: 'ring-primary/30'}"
		>
			<!-- Cluster header: tabs for multiple comments or single author header -->
			<div class="border-text/30 w-full border-b p-1.5 pb-0">
				<div class="border-text/10 pb-0! flex items-center justify-between gap-1.5 border-b">
					<div class="flex flex-wrap items-center gap-1.5">
						{#each comments as c, idx (c.id)}
							{@const state = commentStates.get(c.id)}
							<button
								class="flex cursor-pointer bg-inset flex-row items-center gap-1.5 rounded-t px-2 pt-1.5 pb-1 text-xs font-medium transition-colors
							{activeComment === c
									? 'text-text shadow-inner shadow-text/40'
									: 'text-text/50 hover:bg-text/5 hover:text-text/70 hover:animate-pulse'}"
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
									<PinIcon class="text-text h-4 w-4 transition-colors hover:text-red-400" />
								{:else if c.id === activeComment.id}
									<PinOffIcon class="hover:text-text h-4 w-4" />
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

					{#key hoveredTabCommentState?.id ?? activeCommentState?.id}
						<ConnectionLine
							commentState={hoveredTabCommentState ?? activeCommentState}
							{yPosition}
							{scrollTop}
						/>
					{/key}
				{/if}
			{/if}
		</div>
	{:else}
		{@const badgePreviewUser = highlightHoveredComment?.user ?? authorsInCluster[0]}
		<!-- Compact badge - only hover on badge itself triggers expansion -->
		<div
			role="combobox"
			aria-controls="false"
			aria-expanded="false"
			tabindex={activeComment.id}
			bind:this={clusterRef}
			class="relative z-10 w-fit"
			data-comment-badge={activeComment?.id}
		>
			<div
				class="ring-3 ring-primary/0 {highlightHoveredComment
					? 'ring-primary/70'
					: ''} flex cursor-pointer flex-row items-center justify-start rounded p-1 transition-all"
			>
				<CommentIcon class="text-primary mr-2 h-4 w-4" />
				<p>{badgePreviewUser?.username ?? 'Unknown'}</p>
				{#if authorsInCluster.length > 1}
					<span
						class="bg-primary/10 text-primary ml-2 rounded-full px-2 py-0.5 text-xs font-medium"
					>
						+ {authorsInCluster.length - 1}
					</span>
				{/if}
			</div>
		</div>
	{/if}
</div>
