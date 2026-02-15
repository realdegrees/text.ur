<script lang="ts">
	import { documentStore } from '$lib/runes/document.svelte.js';
	import { SvelteMap } from 'svelte/reactivity';
	import CommentCard from './CommentCard.svelte';
	import PinIcon from '~icons/material-symbols/push-pin';
	import PinOffIcon from '~icons/material-symbols/push-pin-outline';
	import CloseIcon from '~icons/material-symbols/close';
	import type { CommentRead } from '$api/types';
	import { preciseHover } from '$lib/actions/preciseHover';
	import { longPress } from '$lib/actions/longPress';
	import { hasHoverCapability } from '$lib/util/responsive.svelte';
	import { DEFAULT_HIGHLIGHT_COLOR } from './constants';

	interface Props {
		comments: CommentRead[];
		yPosition: number;
		onHeightChange?: (height: number) => void;
		forceExpanded?: boolean;
	}

	let { comments, yPosition, onHeightChange, forceExpanded = false }: Props = $props();

	let commentStates = $derived.by(
		() => new SvelteMap(comments.map((c) => [c.id, documentStore.comments.getState(c.id)]))
	);

	// Track which comment is selected in this group (defaults to first)

	let selectedTabId = $state<number | null>(null);

	let hoveredTabId: number | null = $state(null);
	let hoveredTabCommentState = $derived.by(() => commentStates.get(hoveredTabId ?? -1));
	let highlightHoveredComment: CommentRead | null = $derived.by(() => {
		return comments.find((c) => commentStates.get(c.id)?.isHighlightHovered) ?? null;
	});
	let firstCommentHovered: CommentRead | null = $derived.by(() => {
		return comments.find((c) => commentStates.get(c.id)?.isCommentHovered) ?? null;
	});
	let firstEditingComment: CommentRead | null = $derived.by(() => {
		return comments.find((c) => commentStates.get(c.id)?.isEditing) ?? null;
	});
	let firstReplyingComment: CommentRead | null = $derived.by(() => {
		return comments.find((c) => commentStates.get(c.id)?.isReplying) ?? null;
	});
	let firstPinnedComment: CommentRead | null = $derived.by(() => {
		return comments.find((c) => commentStates.get(c.id)?.isPinned) ?? null;
	});
	let hasPinnedComment = $derived(!!firstPinnedComment);
	let selectedTabComment = $derived.by(() => {
		return comments.find((c) => c.id === selectedTabId) ?? null;
	});

	let activeComment: CommentRead = $derived(
		highlightHoveredComment ??
			firstEditingComment ??
			firstReplyingComment ??
			selectedTabComment ??
			firstPinnedComment ??
			comments[0]
	);

	let activeCommentState = $derived.by(() => commentStates.get(activeComment.id));

	// Border color follows hovered tab if any, otherwise activeComment's first tag
	let hoveredTabComment = $derived.by(() => {
		if (hoveredTabId == null) return null;
		return comments.find((c) => c.id === hoveredTabId) ?? null;
	});

	let activeTagColor = $derived.by(() => {
		const c = hoveredTabComment ?? activeComment;
		return c.tags && c.tags.length > 0 ? c.tags[0].color : DEFAULT_HIGHLIGHT_COLOR;
	});

	// Show expanded card when pinned, editing, replying, or force-expanded
	let showCard = $derived(
		forceExpanded ||
			firstPinnedComment ||
			firstEditingComment ||
			firstReplyingComment ||
			(!hasHoverCapability() && highlightHoveredComment)
	);

	// When a comment gets pinned (e.g. via highlight click), make it the active tab
	// so the cluster shows that comment's card.
	$effect(() => {
		if (firstPinnedComment) {
			selectedTabId = firstPinnedComment.id;
		}
	});

	/** Unpin every comment in this cluster. */
	function unpinAll() {
		for (const c of comments) {
			const state = commentStates.get(c.id);
			if (state) state.isPinned = false;
		}
	}

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

	/**
	 * Determine the comment whose connection line should be shown.
	 * Priority: hovered tab > highlight-hovered > comment-hovered > long-pressed > none.
	 */
	let lineComment: CommentRead | null = $derived.by(() => {
		if (hoveredTabId != null) {
			const c = comments.find((c) => c.id === hoveredTabId);
			if (c) return c;
		}
		if (highlightHoveredComment) return highlightHoveredComment;
		if (firstCommentHovered) return firstCommentHovered;
		// Mobile long-press
		const longPressComment = comments.find((c) => c.id === documentStore.longPressCommentId);
		if (longPressComment) return longPressComment;
		return null;
	});

	// Register/unregister connection lines with the shared overlay.
	// Lines are only visible on hover or long-press (mobile), not when merely pinned.
	$effect(() => {
		const isHovered = !!(hoveredTabCommentState || firstCommentHovered || highlightHoveredComment);
		const shouldShow = isHovered || shouldShowConnectionLineOnMobile();

		// Use the specific comment that triggered the line (not activeComment)
		const targetComment = lineComment ?? activeComment;
		const lineState = documentStore.comments.getState(targetComment.id);
		// Get the highlight color from the triggering comment's first tag
		const tagColor =
			targetComment.tags && targetComment.tags.length > 0
				? targetComment.tags[0].color
				: DEFAULT_HIGHLIGHT_COLOR;
		if (shouldShow && lineState) {
			documentStore.registerLine(targetComment.id, {
				commentState: lineState,
				yPosition,
				isHovered,
				clusterElement: clusterRef,
				color: tagColor
			});
		} else {
			documentStore.unregisterLine(targetComment.id);
		}

		return () => {
			documentStore.unregisterLine(targetComment.id);
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
	<div
		bind:this={clusterRef}
		class="relative z-50 overflow-hidden rounded bg-background shadow-lg ring-2 shadow-black/20 transition-all"
		style="--tw-ring-color: {activeTagColor}{firstPinnedComment ? 'b3' : '4d'};"
		use:longPress={{
			onLongPress: () => {
				if (!hasHoverCapability()) {
					documentStore.activeCommentId = activeComment.id;
					documentStore.longPressCommentId = activeComment.id;
				}
			},
			onRelease: () => {
				if (!hasHoverCapability()) {
					documentStore.longPressCommentId = null;
				}
			},
			duration: 500
		}}
	>
		<!-- Tab bar: always visible -->
		<div class="w-full p-1 {showCard ? 'border-b border-text/30 pb-0' : ''}">
			<div
				class="flex items-center justify-between gap-1 {showCard
					? 'border-b border-text/10 pb-0!'
					: ''}"
			>
				<div class="flex flex-wrap items-center gap-1">
					{#each comments as c, idx (c.id)}
						{@const state = commentStates.get(c.id)}
						<button
							class="flex cursor-pointer flex-row items-center gap-1 bg-inset px-1.5 pt-1 pb-0.5 text-xs font-medium transition-colors
							{showCard ? 'rounded-t' : 'rounded'}
							{showCard && activeComment === c
								? 'text-text shadow-inner shadow-text/40'
								: 'text-text/50 hover:animate-pulse hover:bg-text/5 hover:text-text/70'}"
							onclick={(e) => {
								e.stopPropagation();

								const isMobile = !hasHoverCapability();

								if (isMobile) {
									if (state) {
										const wasPinned = state.isPinned;
										state.isPinned = !state.isPinned;
										if (!wasPinned) {
											documentStore.activeCommentId = c.id;
										}
									}
								} else if (!showCard) {
									// Collapsed: pin to expand and select this tab
									if (state) {
										state.isPinned = true;
									}
									selectedTabId = c.id;
								} else {
									// Expanded: toggle pin if already active, otherwise switch tabs
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
							{:else if showCard && c.id === activeComment.id}
								<PinOffIcon class="h-4 w-4 hover:text-text" />
							{/if}
						</button>
					{/each}
				</div>
				{#if hasPinnedComment}
					<button
						class="flex cursor-pointer items-center self-start rounded p-0.5 text-text/40 transition-colors hover:bg-text/10 hover:text-text/70"
						onclick={(e) => {
							e.stopPropagation();
							unpinAll();
						}}
						title="Close"
					>
						<CloseIcon class="h-4 w-4" />
					</button>
				{/if}
			</div>
		</div>

		<!-- Comment card: only visible when expanded -->
		{#if showCard && activeComment}
			<CommentCard comment={activeComment} />
		{/if}
	</div>
</div>
