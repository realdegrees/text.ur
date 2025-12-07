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
	import { longPress } from '$lib/actions/longPress';
	import { hasHoverCapability } from '$lib/util/responsive.svelte';

	interface Props {
		comments: TypedComment[];
		yPosition: number;
		scrollTop?: number;
		onHeightChange?: (height: number) => void;
		forceExpanded?: boolean;
	}

	let { comments, yPosition, scrollTop, onHeightChange, forceExpanded = false }: Props = $props();

	// List of all unique authors in this cluster
	let authorsInCluster = $derived.by(() => {
		const authorSet = new SvelteMap<number, UserRead>();
		for (const comment of comments) {
			if (comment.user?.id) {
				authorSet.set(comment.user.id, comment.user);
			}
		}
		return Array.from(authorSet.values());
	});

	// TODO as soon as up/downvotes are implemented, show the author with the highest upvoted comment in the preview instead and remove selection by replies entirely (because reply count doesnt really matter since we cant get nested replies as replies are loaded lazy)
	// Select the author to show in the preview, first by highest amount of replies on comment, then by order in cluster (default order is by id which is chronological)
	let previewAuthor = $derived.by(() => {
		let highestReplyCount = -1;
		let highestReplyComment: TypedComment | null = null;
		for (const comment of comments) {
			if (comment.num_replies > 0 && comment.num_replies > highestReplyCount) {
				highestReplyCount = comment.num_replies;
				highestReplyComment = comment;
			}
		}
		return highlightHoveredComment?.user ?? highestReplyComment?.user ?? comments[0]?.user ?? null;
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
		forceExpanded ||
			hoveredTabCommentState ||
			firstPinnedComment ||
			firstEditingComment ||
			firstReplyingComment ||
			firstCommentHovered ||
			(!hasHoverCapability() && highlightHoveredComment)
	);

	/**
	 * On mobile, only show connection line when the comment is being long-pressed
	 */
	function shouldShowConnectionLineOnMobile(): boolean {
		if (hasHoverCapability()) {
			return false; // Not mobile, use desktop logic
		}

		// Check if any of the comments in this cluster is being long-pressed
		return comments.some((c) => c.id === documentStore.longPressCommentId);
	}

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
	class={showCard ? 'w-full' : 'w-fit'}
>
	{#if showCard}
		<!-- Expanded card - hover anywhere on card keeps it open -->
		<div
			bind:this={clusterRef}
			class="relative z-50 overflow-hidden rounded bg-background shadow-lg ring-3 shadow-black/20 transition-all {firstPinnedComment
				? 'ring-primary/70'
				: 'ring-primary/30'}"
			use:longPress={{
				onLongPress: () => {
					if (!hasHoverCapability()) {
						// Mobile: Set active and show connection line on long press start
						documentStore.activeCommentId = activeComment.id;
						documentStore.longPressCommentId = activeComment.id;
					}
				},
				onRelease: () => {
					if (!hasHoverCapability()) {
						// Mobile: Clear long press state
						documentStore.longPressCommentId = null;
					}
				},
				duration: 500
			}}
		>
			<!-- Cluster header: tabs for multiple comments or single author header -->
			<div class="w-full border-b border-text/30 p-1.5 pb-0">
				<div class="flex items-center justify-between gap-1.5 border-b border-text/10 pb-0!">
					<div class="flex flex-wrap items-center gap-1.5">
						{#each comments as c, idx (c.id)}
							{@const state = commentStates.get(c.id)}
							<button
								class="flex cursor-pointer flex-row items-center gap-1.5 rounded-t bg-inset px-2 pt-1.5 pb-1 text-xs font-medium transition-colors
							{activeComment === c
									? 'text-text shadow-inner shadow-text/40'
									: 'text-text/50 hover:animate-pulse hover:bg-text/5 hover:text-text/70'}"
								onclick={(e) => {
									e.stopPropagation();

									const isMobile = !hasHoverCapability();

									if (isMobile) {
										// Mobile: Pin/unpin and set as active only when pinning
										if (state) {
											const wasPinned = state.isPinned;
											state.isPinned = !state.isPinned;

											// Only set as active when pinning (not unpinning)
											if (!wasPinned) {
												documentStore.activeCommentId = c.id;
											}
										}
									} else {
										// Desktop: Pin if already active, otherwise switch tabs
										if (activeComment === c && state) {
											state.isPinned = !state.isPinned;
											return;
										}
										if (state) {
											state.isCommentHovered = hasHoverCapability();
										}
										if (activeCommentState) {
											activeCommentState.isCommentHovered = false;
										}

										selectedTabId = c.id;
									}
								}}
								oncontextmenu={(e) => {
									// Prevent context menu on mobile
									if (!hasHoverCapability()) {
										e.preventDefault();
										e.stopPropagation();
									}
								}}
								onmouseenter={() => {
									hoveredTabId = hasHoverCapability() ? c.id : null;
									if (state) state.isCommentHovered = hasHoverCapability();
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

				{#if hoveredTabCommentState || firstCommentHovered || highlightHoveredComment || shouldShowConnectionLineOnMobile()}
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
		<!-- Compact badge - only hover on badge itself triggers expansion -->
		<button
			onclick={(e) => {
				e.stopPropagation();
				if (activeCommentState) {
					activeCommentState.isPinned	= true;
				}
			}}
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
				<p class="mr-0.5 pb-1 text-xs font-medium text-primary">{comments.length}</p>
				<CommentIcon class="mr-2 h-4 w-4 text-primary" />
				<p class="font-medium text-text">{previewAuthor?.username ?? 'Unknown'}</p>
				{#if authorsInCluster.length > 1}
					<span
						class="ml-2 rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary"
					>
						+ {authorsInCluster.length - 1}
					</span>
				{/if}
			</div>
		</button>
	{/if}
</div>
