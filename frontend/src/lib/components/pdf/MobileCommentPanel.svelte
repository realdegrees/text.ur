<script lang="ts">
	import { documentStore } from '$lib/runes/document.svelte';
	import CommentCluster from './CommentCluster.svelte';
	import TasksPanel from './TasksPanel.svelte';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import LL from '$i18n/i18n-svelte';
	import IconChevronDown from '~icons/material-symbols/keyboard-arrow-down-rounded';
	import IconChevronUp from '~icons/material-symbols/keyboard-arrow-up-rounded';
	import IconPin from '~icons/material-symbols/push-pin-outline';
	import IconComment from '~icons/material-symbols/comment-outline';
	import IconTask from '~icons/material-symbols/task-outline';
	import IconInfo from '~icons/material-symbols/info-outline';
	import { onMount } from 'svelte';
	import { longPress } from '$lib/actions/longPress';

	interface Props {
		activeContentTab: 'comments' | 'tasks' | 'info';
		onTabChange: (tab: 'comments' | 'tasks' | 'info') => void;
	}

	let { activeContentTab, onTabChange }: Props = $props();

	let panelElement: HTMLDivElement | null = $state(null);

	// Update CSS variable for panel height so controls can avoid it
	onMount(() => {
		if (!panelElement) return;

		const resizeObserver = new ResizeObserver((entries) => {
			for (const entry of entries) {
				// Use borderBoxSize if available to include borders/padding, otherwise fallback to contentRect
				const height = entry.borderBoxSize?.[0]?.blockSize ?? entry.contentRect.height;
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

<div
	class="mobile-comment-panel absolute right-0 bottom-0 left-0 z-50 bg-background"
	bind:this={panelElement}
>
	<!-- Content-level tab bar: Info | Tasks | Comments -->
	<div class="flex border-t border-text/10 bg-inset">
		{#if documentStore.loadedDocument?.description?.trim()}
			<button
				class="flex flex-1 items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium transition-colors {activeContentTab ===
				'info'
					? 'border-b-2 border-primary text-primary'
					: 'text-text/50 hover:text-text/70'}"
				onclick={() => onTabChange('info')}
			>
				<IconInfo class="h-3.5 w-3.5" />
				{$LL.pdf.documentInfo()}
			</button>
		{/if}
		{#if documentStore.tasks.length > 0}
			<button
				class="flex flex-1 items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium transition-colors {activeContentTab ===
				'tasks'
					? 'border-b-2 border-primary text-primary'
					: 'text-text/50 hover:text-text/70'}"
				onclick={() => onTabChange('tasks')}
			>
				<IconTask class="h-3.5 w-3.5" />
				{$LL.tasks.title()}
			</button>
		{/if}
		<button
			class="flex flex-1 items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium transition-colors {activeContentTab ===
			'comments'
				? 'border-b-2 border-primary text-primary'
				: 'text-text/50 hover:text-text/70'}"
			onclick={() => onTabChange('comments')}
		>
			<IconComment class="h-3.5 w-3.5" />
			{$LL.tasks.comments()}
		</button>
	</div>

	{#if activeContentTab === 'info'}
		<!-- Info collapse toggle bar -->
		<div class="flex items-center border-b border-text/10 bg-inset">
			<span class="flex-1 px-4 py-2.5 text-sm font-medium text-text/60">
				{$LL.pdf.documentInfo()}
			</span>
			<button
				class="px-4 py-2.5 text-text/60 transition-colors hover:text-text"
				onclick={toggleExpand}
				aria-label={isExpanded ? $LL.pdf.collapseComments() : $LL.pdf.expandComments()}
			>
				{#if isExpanded}
					<IconChevronDown class="h-5 w-5" />
				{:else}
					<IconChevronUp class="h-5 w-5" />
				{/if}
			</button>
		</div>
	{:else if activeContentTab === 'tasks'}
		<!-- Tasks collapse toggle bar -->
		<div class="flex items-center border-b border-text/10 bg-inset">
			<span class="flex-1 px-4 py-2.5 text-sm font-medium text-text/60">
				{$LL.tasks.title()}
			</span>
			<button
				class="px-4 py-2.5 text-text/60 transition-colors hover:text-text"
				onclick={toggleExpand}
				aria-label={isExpanded ? $LL.pdf.collapseComments() : $LL.pdf.expandComments()}
			>
				{#if isExpanded}
					<IconChevronDown class="h-5 w-5" />
				{:else}
					<IconChevronUp class="h-5 w-5" />
				{/if}
			</button>
		</div>
	{:else}
		<!-- Comment sub-tabs: Pinned / All -->
		<div class="flex items-center border-b border-text/10 bg-inset">
			<button
				class="flex flex-1 items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors {activeTab ===
				'pinned'
					? 'border-b-2 border-primary text-primary'
					: 'text-text/60 hover:text-text'}"
				onclick={() => selectTab('pinned')}
				aria-pressed={activeTab === 'pinned'}
			>
				<IconPin class="h-4 w-4" />
				<span>{$LL.pdf.pinned()}</span>
				{#if pinnedComments.length > 0}
					<span class="rounded-full bg-primary/20 px-2 py-0.5 text-xs">{pinnedComments.length}</span
					>
				{/if}
			</button>

			<button
				class="flex flex-1 items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors {activeTab ===
				'all'
					? 'border-b-2 border-primary text-primary'
					: 'text-text/60 hover:text-text'}"
				onclick={() => selectTab('all')}
				aria-pressed={activeTab === 'all'}
			>
				<IconComment class="h-4 w-4" />
				<span>{$LL.pdf.all()}</span>
				<span class="rounded-full bg-primary/20 px-2 py-0.5 text-xs"
					>{documentStore.comments.topLevelComments.length}</span
				>
			</button>

			<!-- Expand/Collapse button -->
			<button
				class="px-4 py-2.5 text-text/60 transition-colors hover:text-text"
				onclick={toggleExpand}
				aria-label={isExpanded ? $LL.pdf.collapseComments() : $LL.pdf.expandComments()}
			>
				{#if isExpanded}
					<IconChevronDown class="h-5 w-5" />
				{:else}
					<IconChevronUp class="h-5 w-5" />
				{/if}
			</button>
		</div>
	{/if}

	<!-- Content area - slides up/down -->
	<div
		class="overflow-y-auto transition-all duration-300 ease-in-out {isExpanded
			? 'h-[40vh]'
			: 'h-0'}"
	>
		{#if activeContentTab === 'info'}
			<div class="px-3 py-2">
				<MarkdownRenderer
					content={documentStore.loadedDocument?.description ?? ''}
					class="text-sm text-text/80"
				/>
			</div>
		{:else if activeContentTab === 'tasks'}
			<TasksPanel />
		{:else}
			<div class="p-4">
				{#if displayedComments.length > 0}
					<div class="space-y-3">
						{#each displayedComments as comment (comment.id)}
							<div
								data-comment-id={comment.id}
								class={comment.id === documentStore.activeCommentId
									? 'rounded ring-5 ring-secondary'
									: ''}
								use:longPress={{
									onLongPress: () => handleCommentLongPress(comment.id),
									onRelease: handleCommentLongPressRelease,
									duration: 500
								}}
							>
								<CommentCluster comments={[comment]} forceExpanded={true} />
							</div>
						{/each}
					</div>
				{:else}
					<div class="py-8 text-center text-sm text-text/40">
						{#if activeTab === 'pinned'}
							{$LL.pdf.noPinnedComments()}
						{:else}
							{$LL.pdf.noComments()}
						{/if}
					</div>
				{/if}
			</div>
		{/if}
	</div>
</div>

<style>
	.mobile-comment-panel {
		/* Ensure panel is above PDF content */
		box-shadow: 0 -4px 12px rgba(0, 0, 0, 0.1);
	}
</style>
