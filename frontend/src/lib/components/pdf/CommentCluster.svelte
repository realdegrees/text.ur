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
		onHeightChange?: (height: number) => void;
		forceExpanded?: boolean;
	}

	let { comments, onHeightChange, forceExpanded = false }: Props = $props();

	let commentStates = $derived.by(
		() => new SvelteMap(comments.map((c) => [c.id, documentStore.comments.getState(c.id)]))
	);

	// Track which comment is selected in this group (defaults to first)

	let selectedTabId = $state<number | null>(null);
	let isClusterHovered = $state(false);

	let hoveredTabId: number | null = $state(null);
	let highlightHoveredComment: CommentRead | null = $derived.by(() => {
		return comments.find((c) => commentStates.get(c.id)?.isHighlightHovered) ?? null;
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

	// Register cluster element refs so ConnectionLines can find them.
	// Each comment in this cluster maps to the same clusterRef element.
	$effect(() => {
		const el = clusterRef;
		if (!el) return;

		const ids = comments.map((c) => c.id);
		for (const id of ids) {
			documentStore.clusterElements.set(id, el);
		}

		return () => {
			for (const id of ids) {
				documentStore.clusterElements.delete(id);
			}
		};
	});
</script>

<div
	tabindex="-1"
	use:preciseHover={{
		onEnter: () => (isClusterHovered = true),
		onLeave: () => (isClusterHovered = false)
	}}
	data-comment-badge={activeComment?.id}
	data-badge-active="true"
	class="w-fit"
>
	<div
		bind:this={clusterRef}
		class="relative z-50 overflow-hidden rounded bg-background shadow-lg {showCard
			? 'ring-[2.5px]'
			: 'ring-2'} shadow-black/20 transition-shadow"
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
						{@const tabColor =
							c.tags && c.tags.length > 0 ? c.tags[0].color : DEFAULT_HIGHLIGHT_COLOR}
						{@const isVisuallyHovered = state?.isCommentHovered || state?.isHighlightHovered}
						<button
							class="flex cursor-pointer flex-row items-center gap-1 bg-inset px-1.5 pt-1 pb-0.5 text-xs font-medium transition-colors
							{showCard ? 'rounded-t' : 'rounded'}
							{showCard && activeComment === c
								? 'text-text shadow-inner shadow-text/40'
								: isVisuallyHovered
									? 'bg-text/10 text-text ring-1'
									: 'text-text/50 hover:bg-text/10 hover:text-text hover:ring-1'}"
							style="--tw-ring-color: {tabColor}80;"
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
								} else if (activeComment === c) {
									// Expanded, clicking the active tab: toggle its pin
									if (state) {
										state.isPinned = !state.isPinned;
									}
								} else {
									// Expanded, clicking an inactive tab: just switch to it
									selectedTabId = c.id;
								}
							}}
							oncontextmenu={(e) => {
								if (!hasHoverCapability()) {
									e.preventDefault();
									e.stopPropagation();
								}
							}}
							use:preciseHover={{
								onEnter: () => {
									hoveredTabId = c.id;
									if (state) state.isCommentHovered = true;
								},
								onLeave: () => {
									if (hoveredTabId === c.id) hoveredTabId = null;
									if (state) state.isCommentHovered = false;
								}
							}}
						>
							<div class="flex items-center">
								{#if state?.isPinned && (isClusterHovered || state?.isHighlightHovered)}
									<PinIcon class="h-4 w-4 text-text transition-colors hover:text-red-400" />
									<p class="ml-1">{c.user?.username?.slice(0, 10) ?? `Comment ${idx + 1}`}</p>
								{:else if showCard && c.id === activeComment.id && (isClusterHovered || state?.isHighlightHovered)}
									<PinOffIcon class="h-4 w-4 hover:text-text" />
									<p class="ml-1">{c.user?.username?.slice(0, 10) ?? `Comment ${idx + 1}`}</p>
								{:else}
									<p>{c.user?.username?.slice(0, 10) ?? `Comment ${idx + 1}`}</p>
								{/if}
							</div>
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
