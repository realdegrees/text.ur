<script lang="ts">
	import { untrack } from 'svelte';
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
	let hoveredCommentInGroup = $derived(
		comments.find(c => c.isHighlightHovered)
	);

	// Check if any comment in this cluster is pinned
	let pinnedCommentInGroup = $derived(
		comments.find(c => c.isPinned)
	);

	// When a highlight is hovered, switch to that comment's tab
	$effect(() => {
		if (hoveredCommentInGroup) {
			const idx = comments.findIndex(c => c.id === hoveredCommentInGroup.id);
			if (idx !== -1) {
				selectedIndex = idx;
			}
		}
	});

	// When a comment is pinned in this group, switch to that tab
	$effect(() => {
		if (pinnedCommentInGroup) {
			const idx = comments.findIndex(c => c.id === pinnedCommentInGroup.id);
			if (idx !== -1) {
				selectedIndex = idx;
			}
		}
	});

	// Show expanded card when badge is hovered, highlight is hovered, or comment is pinned
	let showCard = $derived(isHovered || !!hoveredCommentInGroup || !!pinnedCommentInGroup);

	// Update the store's selected comment when this card is shown via badge hover
	// Use untrack to prevent infinite loops when modifying store state
	$effect(() => {
		// Only track isHovered and selectedIndex as dependencies
		const hovered = isHovered;
		const idx = selectedIndex;

		// Use untrack for store reads/writes to avoid circular dependencies
		untrack(() => {
			const comment = comments[idx];
			if (hovered && comment) {
				// Clear any existing pinned comment from other badges when this one is hovered
				const pinned = documentStore.pinnedComment;
				const pinnedInGroup = comments.find(c => c.isPinned);
				if (pinned && !pinnedInGroup) {
					documentStore.setPinned(null);
				}
				// Set active and selected when badge is hovered
				documentStore.setCommentCardActive(true);
				documentStore.setBadgeHovered(comment.id);
				documentStore.setSelected(comment.id);
			} else {
				const pinnedInGroup = comments.find(c => c.isPinned);
				const comment = comments[idx];
				if (pinnedInGroup && comment) {
					// Set active when pinned
					documentStore.setCommentCardActive(true);
					documentStore.setSelected(comment.id);
				}
			}
		});
	});

	// Clear selected comment when card closes (but not if pinned)
	const handleMouseLeave = () => {
		isHovered = false;
		documentStore.setBadgeHovered(null);
		// Small delay to allow for moving to another badge
		setTimeout(() => {
			if (!isHovered && !hoveredCommentInGroup && !pinnedCommentInGroup) {
				documentStore.setSelected(null);
				documentStore.setCommentCardActive(false);
			}
		}, 50);
	};

	// Handle click to pin/unpin the comment
	const handleClick = () => {
		const currentComment = comments[selectedIndex];
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
		selectedIndex = index;
		if (comments[index]) {
			// Mark as active since user is interacting with the comment card
			documentStore.setCommentCardActive(true);
			documentStore.setSelected(comments[index].id);
			// Also pin to this comment when clicking tabs
			documentStore.setPinned(comments[index].id);
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
		data-comment-badge={comments[selectedIndex]?.id}
		data-badge-active="true"
		onmouseleave={handleMouseLeave}
	>
		<CommentCard {comments} activeIndex={selectedIndex} onSelectionChange={handleSelectionChange} />
	</div>
{:else}
	<!-- Compact badge - only hover on badge itself triggers expansion -->
	<div
		class="relative z-10 inline-block"
		role="button"
		tabindex="0"
		data-comment-badge={comments[selectedIndex]?.id}
		onmouseenter={() => (isHovered = true)}
		onmouseleave={handleMouseLeave}
		onfocus={() => (isHovered = true)}
		onblur={handleMouseLeave}
		onclick={handleClick}
		onkeydown={handleKeydown}
	>
		<div
			class="flex h-8 w-8 cursor-pointer items-center justify-center rounded-full border-2 border-background bg-secondary shadow-md transition-transform hover:scale-110"
		>
			{#if commentCount > 1}
				<span class="text-xs font-bold text-text">{commentCount}</span>
			{:else}
				<CommentIcon class="h-4 w-4 text-text" />
			{/if}
		</div>
	</div>
{/if}
