<script lang="ts">
	/*
  Presentational component to render the body of a single comment with edit/reply/nested replies.
  Extracted to avoid duplicated UI between CommentCard.svelte and CommentGroup.svelte.
  */
	import type { CommentRead } from '$api/types';
	import type { Annotation } from '$types/pdf';
	import { commentStore } from '$lib/stores/commentStore';
	import CommentBody from './CommentBody.svelte';
	import MarkdownEditor from '$lib/components/pdf/MarkdownEditor.svelte';
	import { renderMarkdown } from '$lib/util/markdown';
	import DeleteIcon from '~icons/material-symbols/delete-outline';
	import EditIcon from '~icons/material-symbols/edit-outline';
	import ReplyIcon from '~icons/material-symbols/reply';
	import SaveIcon from '~icons/material-symbols/save-outline';
	import CancelIcon from '~icons/material-symbols/cancel-outline';
	import ExpandMoreIcon from '~icons/material-symbols/expand-more';
	import { browser } from '$app/environment';

	interface Props {
		comment: CommentRead;
		annotation: Annotation | null;
		showDeleteConfirm: boolean;
		depth?: number;
		onDeleteClick?: (event: MouseEvent) => void;
		onDeleteConfirm?: (event: MouseEvent) => void;
		onDeleteCancel?: (event: MouseEvent) => void;
	}

	let {
		comment,
		annotation = null,
		showDeleteConfirm = false,
		depth = 0,
		onDeleteClick = () => {},
		onDeleteConfirm = () => {},
		onDeleteCancel = () => {}
	}: Props = $props();

	// Get currentUserId from store
	const currentUserId = commentStore.getCurrentUserId();

	// Edit/reply state
	let isEditing = $state(false);
	let isReplying = $state(false);
	let editContent = $state(comment.content || '');
	let replyContent = $state('');
	let isSaving = $state(false);

	// Reply loading state
	let isLoadingReplies = $state(false);
	let loadedReplies = $state<CommentRead[]>([]);
	let hasLoadedReplies = $state(false);

	// Delete state for nested replies
	let deleteConfirmReplyId = $state<number | null>(null);

	// Subscribe to cache version for reactivity
	let cacheVersion = $state(0);
	commentStore.subscribeToCacheVersion((v) => {
		cacheVersion = v;
	});

	// Check for cached replies on mount or when comment/cache changes
	// Also updates when cache is modified (create/delete operations)
	$effect(() => {
		// Read cacheVersion to trigger reactivity when cache changes
		void cacheVersion;
		const cachedReplies = commentStore.getCachedReplies(comment.id);
		if (cachedReplies !== undefined) {
			loadedReplies = cachedReplies;
			if (cachedReplies.length > 0) {
				hasLoadedReplies = true;
			}
		}
	});

	// Check if current user owns this comment
	let isOwnComment = $derived(currentUserId !== null && comment.user?.id === currentUserId);

	// Render comment content as markdown using shared utility
	let renderedContent = $derived.by(() => {
		if (!browser || !comment.content) return '';
		return renderMarkdown(comment.content);
	});

	// Determine which replies to show (only use async loaded replies)
	let displayedReplies = $derived(hasLoadedReplies ? loadedReplies : []);

	// Show "Load more replies" button for any comment with unloaded replies at any depth
	// Check: hasn't loaded, not loading, no displayed replies, and num_replies indicates there are replies
	let shouldShowLoadMoreButton = $derived(
		!hasLoadedReplies &&
			!isLoadingReplies &&
			displayedReplies.length === 0 &&
			comment.num_replies > 0
	);

	// Format timestamp
	function formatDate(dateString: string | undefined): string {
		if (!dateString) return '';
		const date = new Date(dateString);
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffMins = Math.floor(diffMs / 60000);
		const diffHours = Math.floor(diffMs / 3600000);
		const diffDays = Math.floor(diffMs / 86400000);

		if (diffMins < 1) return 'just now';
		if (diffMins < 60) return `${diffMins}m ago`;
		if (diffHours < 24) return `${diffHours}h ago`;
		if (diffDays < 7) return `${diffDays}d ago`;
		return date.toLocaleDateString();
	}

	// Handlers
	function handleEditClick() {
		editContent = comment.content || '';
		isEditing = true;
	}

	function handleCancelEdit() {
		isEditing = false;
		editContent = comment.content || '';
	}

	async function handleSaveEdit() {
		if (isSaving) return;
		isSaving = true;
		try {
			await commentStore.update(comment.id, { content: editContent.trim() });
			isEditing = false;
		} finally {
			isSaving = false;
		}
	}

	function handleReplyClick() {
		isReplying = !isReplying;
		replyContent = '';
	}

	function handleCancelReply() {
		isReplying = false;
		replyContent = '';
	}

	async function handleSaveReply() {
		if (isSaving || !replyContent.trim()) return;
		isSaving = true;
		try {
			await commentStore.create({
				parentId: comment.id,
				content: replyContent.trim(),
				visibility: 'public'
			});
			isReplying = false;
			replyContent = '';
			// Cache will be updated automatically, triggering reactivity
		} finally {
			isSaving = false;
		}
	}

	// Load replies for this comment
	async function loadReplies(forceRefresh: boolean = false) {
		if (isLoadingReplies) return;

		isLoadingReplies = true;

		try {
			loadedReplies = await commentStore.loadReplies(comment.id, forceRefresh);
			hasLoadedReplies = true;
		} catch (err) {
			console.error('Failed to load replies:', err);
		} finally {
			isLoadingReplies = false;
		}
	}

	// Handle delete for nested replies
	function handleReplyDeleteClick(replyId: number) {
		deleteConfirmReplyId = replyId;
	}

	async function handleReplyDeleteConfirm(replyId: number) {
		if (isSaving) return;
		isSaving = true;
		try {
			await commentStore.delete(replyId, comment.id);
			deleteConfirmReplyId = null;
			// Cache will be updated automatically, triggering reactivity
		} finally {
			isSaving = false;
		}
	}

	function handleReplyDeleteCancel() {
		deleteConfirmReplyId = null;
	}

	// Reset loaded replies state when comment changes (for tab switching in groups)
	let previousCommentId = $state(comment.id);
	$effect(() => {
		if (comment.id !== previousCommentId) {
			// Comment changed, check for cached replies or reset
			const cachedReplies = commentStore.getCachedReplies(comment.id);
			if (cachedReplies) {
				loadedReplies = cachedReplies;
				hasLoadedReplies = true;
			} else {
				hasLoadedReplies = false;
				loadedReplies = [];
			}
			isLoadingReplies = false;
			previousCommentId = comment.id;
		}
	});
</script>

{#if showDeleteConfirm}
	<div
		class="flex flex-col gap-2"
		onclick={(e) => e.stopPropagation()}
		onkeydown={(e) => {
			if (e.key === 'Escape') {
				onDeleteCancel(e as any);
			}
		}}
		role="dialog"
		aria-label="Delete confirmation"
		tabindex="-1"
	>
		<p class="text-sm font-semibold text-accent">Delete this comment?</p>
		<div class="flex gap-2">
			<button
				onclick={onDeleteConfirm}
				disabled={isSaving}
				class="rounded-md bg-accent px-3 py-1.5 text-xs font-semibold text-background transition-colors hover:brightness-90 disabled:opacity-50"
			>
				{isSaving ? 'Deleting...' : 'Delete'}
			</button>
			<button
				onclick={onDeleteCancel}
				disabled={isSaving}
				class="rounded-md bg-inset px-3 py-1.5 text-xs font-semibold text-text transition-colors hover:bg-text/10 disabled:opacity-50"
			>
				Cancel
			</button>
		</div>
	</div>
{:else}
	<div>
		<!-- Comment header -->
		<div class="mb-2 flex items-center justify-between">
			<div class="flex items-center gap-2">
				{#if annotation}
					<div class="h-3 w-3 rounded-full" style:background-color={annotation.color}></div>
				{/if}
				<span class="text-xs font-semibold text-text">
					{comment.user?.username ?? 'Anonymous'}
				</span>
				<span class="text-xs text-text/60">{formatDate(comment.created_at)}</span>
				{#if comment.updated_at && comment.updated_at !== comment.created_at}
					<span class="text-xs italic text-text/40">(edited)</span>
				{/if}
			</div>
			<div class="flex gap-1">
				{#if isOwnComment && !isEditing}
					<button
						onclick={handleEditClick}
						class="rounded p-1 text-text/40 transition-colors hover:bg-inset hover:text-text"
						aria-label="Edit comment"
						title="Edit"
					>
						<EditIcon class="h-4 w-4" />
					</button>
				{/if}
				{#if isOwnComment}
					<button
						onclick={onDeleteClick}
						class="rounded p-1 text-text/40 transition-colors hover:bg-inset hover:text-accent"
						aria-label="Delete comment"
						title="Delete"
					>
						<DeleteIcon class="h-4 w-4" />
					</button>
				{/if}
			</div>
		</div>

		<!-- Highlighted text preview (only for comments with annotations) -->
		{#if annotation?.text}
			<p class="mb-2 text-xs italic text-text/60">
				"{annotation.text.substring(0, 100)}{annotation.text.length > 100 ? '...' : ''}"
			</p>
		{/if}

		<!-- Comment content (edit mode or display) -->
		{#if isEditing}
			<div class="mb-2 flex flex-col gap-2">
				<MarkdownEditor
					bind:value={editContent}
					placeholder="Edit your comment..."
					minHeight="8rem"
					disabled={isSaving}
				/>
				<div class="flex gap-2">
					<button
						onclick={handleSaveEdit}
						disabled={isSaving || !editContent.trim()}
						class="flex items-center gap-1 rounded bg-primary px-2 py-1 text-xs font-semibold text-background transition-colors hover:bg-accent disabled:opacity-50"
					>
						<SaveIcon class="h-3 w-3" />
						{isSaving ? 'Saving...' : 'Save'}
					</button>
					<button
						onclick={handleCancelEdit}
						disabled={isSaving}
						class="flex items-center gap-1 rounded bg-inset px-2 py-1 text-xs font-semibold text-text transition-colors hover:bg-text/10 disabled:opacity-50"
					>
						<CancelIcon class="h-3 w-3" />
						Cancel
					</button>
				</div>
			</div>
		{:else}
			<div class="mb-2">
				{#if comment.content}
					<div class="prose prose-sm max-w-none text-sm leading-relaxed text-text">
						<!-- eslint-disable-next-line svelte/no-at-html-tags -->
						{@html renderedContent}
					</div>
				{:else}
					<p class="text-xs italic text-text/40">No comment added</p>
				{/if}
			</div>

			<!-- Reply button -->
			<button
				onclick={handleReplyClick}
				class="flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-text/70 transition-colors hover:bg-inset"
			>
				<ReplyIcon class="h-3 w-3" />
				Reply
			</button>
		{/if}

		<!-- Reply form -->
		{#if isReplying}
			<div class="mt-2 rounded border border-primary/30 bg-secondary/20 p-2">
				<MarkdownEditor
					bind:value={replyContent}
					placeholder="Write a reply..."
					minHeight="6rem"
					disabled={isSaving}
				/>
				<div class="mt-2 flex gap-2">
					<button
						onclick={handleSaveReply}
						disabled={isSaving || !replyContent.trim()}
						class="rounded bg-primary px-2 py-1 text-xs font-semibold text-background transition-colors hover:bg-accent disabled:opacity-50"
					>
						{isSaving ? 'Posting...' : 'Post Reply'}
					</button>
					<button
						onclick={handleCancelReply}
						disabled={isSaving}
						class="rounded bg-inset px-2 py-1 text-xs font-semibold text-text transition-colors hover:bg-text/10 disabled:opacity-50"
					>
						Cancel
					</button>
				</div>
			</div>
		{/if}

		<!-- Load more replies button for nested comments -->
		{#if shouldShowLoadMoreButton}
			<button
				onclick={() => loadReplies()}
				class="mt-2 flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-primary transition-colors hover:bg-secondary/30"
			>
				<ExpandMoreIcon class="h-3 w-3" />
				Load {comment.num_replies} {comment.num_replies === 1 ? 'reply' : 'replies'}
			</button>
		{/if}

		<!-- Loading indicator for replies -->
		{#if isLoadingReplies && !hasLoadedReplies}
			<div class="mt-3 flex items-center gap-2 text-xs text-text/60">
				<div
					class="h-3 w-3 animate-spin rounded-full border-2 border-text/20 border-t-primary"
				></div>
				Loading replies...
			</div>
		{/if}

		<!-- Recursive replies -->
		{#if displayedReplies.length > 0}
			<div class="mt-3 space-y-2 border-l-2 border-text/10 pl-3">
				{#each displayedReplies as reply (reply.id)}
					<CommentBody
						comment={reply}
						annotation={(reply.annotation as unknown as Annotation) || null}
						showDeleteConfirm={deleteConfirmReplyId === reply.id}
						depth={depth + 1}
						onDeleteClick={() => handleReplyDeleteClick(reply.id)}
						onDeleteConfirm={() => handleReplyDeleteConfirm(reply.id)}
						onDeleteCancel={handleReplyDeleteCancel}
					/>
				{/each}
			</div>
		{/if}
	</div>
{/if}
