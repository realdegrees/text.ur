<script lang="ts">
	import { documentStore } from '$lib/runes/document.svelte';
	import CommentCluster from './CommentCluster.svelte';
	import IconChevronDown from '~icons/material-symbols/keyboard-arrow-down-rounded';
	import IconChevronUp from '~icons/material-symbols/keyboard-arrow-up-rounded';
	import IconPin from '~icons/material-symbols/push-pin-outline';
	import IconComment from '~icons/material-symbols/comment-outline';
	import { onMount } from 'svelte';
	import { longPress } from '$lib/actions/longPress';

	interface Props {
		scrollTop: number;
	}

	let { scrollTop }: Props = $props();

	let panelElement: HTMLDivElement | null = $state(null);

	// Update CSS variable for panel height so controls can avoid it
	onMount(() => {
		if (!panelElement) return;

		const resizeObserver = new ResizeObserver((entries) => {
			for (const entry of entries) {
				const height = entry.contentRect.height;
				document.documentElement.style.setProperty('--mobile-comment-panel-height', `${height}px`);
			}
		});

		resizeObserver.observe(panelElement);

		return () => {
			resizeObserver.disconnect();
			document.documentElement.style.removeProperty('--mobile-comment-panel-height');
		};
	});

	type Tab = 'pinned' | 'all';
	let activeTab = $state<Tab>('all');
	let isExpanded = $state(false);

	// Get all pinned comments
	let pinnedComments = $derived.by(() => {
		return documentStore.comments.topLevelComments.filter((comment) => {
			const state = documentStore.comments.getState(comment.id);
			return state?.isPinned;
		});
	});

	// Determine which comments to show based on active tab
	let displayedComments = $derived.by(() => {
		if (activeTab === 'pinned') return pinnedComments;
		return documentStore.comments.topLevelComments; // 'all' tab
	});

	// When active comment changes, expand panel and scroll to it
	$effect(() => {
		const activeId = documentStore.activeCommentId;
		if (activeId !== null) {
			// Expand panel
			isExpanded = true;

			// Switch to All tab (don't auto-switch to pinned)
			activeTab = 'all';

			// Scroll to comment in list
			scrollToCommentInList(activeId);

			// Scroll PDF to highlight
			documentStore.scrollToComment(activeId);
		}
	});

	function toggleExpand() {
		isExpanded = !isExpanded;
	}

	function selectTab(tab: Tab) {
		activeTab = tab;
		if (!isExpanded) {
			isExpanded = true;
		}
	}

	function handleCommentLongPress(commentId: number) {
		// Set active and show connection line on long press start
		documentStore.activeCommentId = commentId;
		documentStore.longPressCommentId = commentId;
	}

	function handleCommentLongPressRelease() {
		// Clear long press state
		documentStore.longPressCommentId = null;
	}

	/**
	 * Scroll to a comment in the mobile panel list
	 */
	function scrollToCommentInList(commentId: number) {
		// Wait for DOM update, then scroll to the comment
		setTimeout(() => {
			const commentElement = panelElement?.querySelector(`[data-comment-id="${commentId}"]`);
			if (commentElement) {
				commentElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
			}
		}, 100);
	}
</script>

<div class="mobile-comment-panel fixed bottom-0 left-0 right-0 z-50 bg-background" bind:this={panelElement}>
	<!-- Tab bar / Header - always visible -->
	<div class="flex items-center border-b border-t border-text/10 bg-inset">
		<!-- Tabs -->
		<button
			class="flex flex-1 items-center justify-center gap-2 px-4 py-3 text-sm font-medium transition-colors {activeTab ===
			'pinned'
				? 'border-b-2 border-primary text-primary'
				: 'text-text/60 hover:text-text'}"
			onclick={() => selectTab('pinned')}
			aria-pressed={activeTab === 'pinned'}
		>
			<IconPin class="h-4 w-4" />
			<span>Pinned</span>
			{#if pinnedComments.length > 0}
				<span class="rounded-full bg-primary/20 px-2 py-0.5 text-xs"
					>{pinnedComments.length}</span
				>
			{/if}
		</button>

		<button
			class="flex flex-1 items-center justify-center gap-2 px-4 py-3 text-sm font-medium transition-colors {activeTab ===
			'all'
				? 'border-b-2 border-primary text-primary'
				: 'text-text/60 hover:text-text'}"
			onclick={() => selectTab('all')}
			aria-pressed={activeTab === 'all'}
		>
			<IconComment class="h-4 w-4" />
			<span>All</span>
			<span class="rounded-full bg-primary/20 px-2 py-0.5 text-xs"
				>{documentStore.comments.topLevelComments.length}</span
			>
		</button>

		<!-- Expand/Collapse button -->
		<button
			class="px-4 py-3 text-text/60 transition-colors hover:text-text"
			onclick={toggleExpand}
			aria-label={isExpanded ? 'Collapse comments' : 'Expand comments'}
		>
			{#if isExpanded}
				<IconChevronDown class="h-5 w-5" />
			{:else}
				<IconChevronUp class="h-5 w-5" />
			{/if}
		</button>
	</div>

	<!-- Content area - slides up/down -->
	<div
		class="overflow-y-auto transition-all duration-300 ease-in-out {isExpanded
			? 'h-[40vh]'
			: 'h-0'}"
	>
		<div class="p-4">
			{#if displayedComments.length > 0}
				<div class="space-y-3">
					{#each displayedComments as comment (comment.id)}
						<div
							data-comment-id={comment.id}
							class="{comment.id === documentStore.activeCommentId
								? 'rounded ring-2 ring-primary'
								: ''}"
							use:longPress={{
								onLongPress: () => handleCommentLongPress(comment.id),
								onRelease: handleCommentLongPressRelease,
								duration: 500
							}}
						>
							<CommentCluster comments={[comment]} yPosition={0} {scrollTop} forceExpanded={true} />
						</div>
					{/each}
				</div>
			{:else}
				<div class="py-8 text-center text-sm text-text/40">
					{#if activeTab === 'pinned'}
						No pinned comments
					{:else}
						No comments
					{/if}
				</div>
			{/if}
		</div>
	</div>
</div>

<style>
	.mobile-comment-panel {
		/* Ensure panel is above PDF content */
		box-shadow: 0 -4px 12px rgba(0, 0, 0, 0.1);
	}
</style>
