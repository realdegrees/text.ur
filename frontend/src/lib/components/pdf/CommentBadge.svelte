<script lang="ts">
	import { documentStore, type CachedComment } from '$lib/runes/document.svelte.js';
	import CommentCard from './CommentCard.svelte';
	import CommentIcon from '~icons/material-symbols/comment-outline';

	interface Props {
		comments: CachedComment[];
	}

	let { comments }: Props = $props();

	let isHovered = $state(false);

	// Track which comment is selected in this group (defaults to first)
	let selectedIndex = $state(0);

	// Check if any comment in this cluster is hovered (via annotation highlight)
	let hoveredCommentInGroup = $derived(comments.find((c) => c.isHighlightHovered));

	// Check if any comment in this cluster is pinned
	let pinnedCommentInGroup = $derived(comments.find((c) => c.isPinned));

	// Derive selectedIndex from external state (highlight hover or pinned)
	// This is read-only synchronization - no store writes here
	let effectiveSelectedIndex = $derived.by(() => {
		// Priority: pinned > hovered highlight > local selection
		if (pinnedCommentInGroup) {
			const idx = comments.findIndex((c) => c.id === pinnedCommentInGroup.id);
			if (idx !== -1) return idx;
		}
		if (hoveredCommentInGroup) {
			const idx = comments.findIndex((c) => c.id === hoveredCommentInGroup.id);
			if (idx !== -1) return idx;
		}
		return selectedIndex;
	});

	// Check if any comment in this group has active input (editing or replying)
	let hasActiveInputInGroup = $derived(
		comments.some((c) => c.isEditing || documentStore.replyingToCommentId === c.id)
	);

	// Show expanded card when badge is hovered, highlight is hovered, comment is pinned, or input is active
	let showCard = $derived(
		isHovered || !!hoveredCommentInGroup || !!pinnedCommentInGroup || hasActiveInputInGroup
	);

	// Handle mouse enter - set store state
	const handleMouseEnter = () => {
		isHovered = true;
		const comment = comments[effectiveSelectedIndex];
		if (comment) {
			// Clear any existing pinned comment from other badges when this one is hovered
			const pinned = documentStore.pinnedComment;
			const hasPinnedInGroup = comments.some((c) => c.isPinned);
			if (pinned && !hasPinnedInGroup) {
				documentStore.setPinned(null);
			}
			documentStore.setCommentCardActive(true);
			documentStore.setBadgeHovered(comment.id);
			documentStore.setSelected(comment.id);
		}
	};

	// Clear selected comment when card closes (but not if pinned or input active)
	const handleMouseLeave = () => {
		isHovered = false;
		// Don't update badge hover state if there's active input - it triggers re-render and loses focus
		if (!hasActiveInputInGroup) {
			documentStore.setBadgeHovered(null);
		}
		// Small delay to allow for moving to another badge
		setTimeout(() => {
			// Don't auto-close if there's an active input (editing or replying)
			if (
				!isHovered &&
				!hoveredCommentInGroup &&
				!pinnedCommentInGroup &&
				!documentStore.hasActiveInput
			) {
				documentStore.setSelected(null);
				documentStore.setCommentCardActive(false);
			}
		}, 50);
	};

	// Handle click to pin/unpin the comment
	const handleClick = () => {
		const currentComment = comments[effectiveSelectedIndex];
		if (currentComment) {
			if (currentComment.isPinned) {
				// Already pinned, unpin it
				documentStore.setPinned(null);
			} else {
				// Pin this comment
				documentStore.setPinned(currentComment.id);
				documentStore.setCommentCardActive(true);
				documentStore.setSelected(currentComment.id);
			}
		}
	};

	let commentCount = $derived(comments.length);

	// Handler for when tab selection changes in CommentCard (user clicked a tab)
	const handleSelectionChange = (index: number) => {
		const comment = comments[index];
		if (comment) {
			// Update local state first so UI responds immediately
			selectedIndex = index;
			// Then update store state
			documentStore.setCommentCardActive(true);
			documentStore.setSelected(comment.id);
			// Also pin to this comment when clicking tabs
			documentStore.setPinned(comment.id);
		}
	};

	// Handle keyboard events for accessibility
	const handleKeydown = (e: KeyboardEvent) => {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			handleClick();
		}
	};
</script>

{#if showCard}
	<!-- Expanded card - hover anywhere on card keeps it open -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="relative z-50"
		data-comment-badge={comments[effectiveSelectedIndex]?.id}
		data-badge-active="true"
		onmouseleave={handleMouseLeave}
	>
		<CommentCard
			{comments}
			activeIndex={effectiveSelectedIndex}
			onSelectionChange={handleSelectionChange}
		/>
	</div>
{:else}
	<!-- Compact badge - only hover on badge itself triggers expansion -->
	<div
		class="relative z-10 inline-block"
		role="button"
		tabindex="0"
		data-comment-badge={comments[effectiveSelectedIndex]?.id}
		onmouseenter={handleMouseEnter}
		onmouseleave={handleMouseLeave}
		onfocus={handleMouseEnter}
		onblur={handleMouseLeave}
		onclick={handleClick}
		onkeydown={handleKeydown}
	>
		<div
			class="flex h-8 w-8 cursor-pointer items-center justify-center rounded-full border-2 border-background bg-secondary shadow-md shadow-black/20 drop-shadow-xs transition-transform hover:scale-110"
		>
			{#if commentCount > 1}
				<span class="text-xs font-bold text-text">{commentCount}</span>
			{:else}
				<CommentIcon class="h-4 w-4 text-text" />
			{/if}
		</div>
	</div>
{/if}
