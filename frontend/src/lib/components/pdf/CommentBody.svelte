<script lang="ts">
	/*
  Presentational component to render the body of a single comment with edit/reply/nested replies.
  Extracted to avoid duplicated UI between CommentCard.svelte and CommentGroup.svelte.
  */
	import type { CommentRead, CommentCreate, CommentUpdate } from '$api/types';
	import type { Annotation } from '$types/pdf';
	import type { Paginated } from '$api/pagination';
	import { api } from '$api/client';
	import { notification } from '$lib/stores/notificationStore';
	import CommentBody from './CommentBody.svelte';
	import DeleteIcon from '~icons/material-symbols/delete-outline';
	import EditIcon from '~icons/material-symbols/edit-outline';
	import ReplyIcon from '~icons/material-symbols/reply';
	import SaveIcon from '~icons/material-symbols/save-outline';
	import CancelIcon from '~icons/material-symbols/cancel-outline';
	import ExpandMoreIcon from '~icons/material-symbols/expand-more';

	interface Props {
		comment: CommentRead;
		annotation: Annotation | null;
		showDeleteConfirm: boolean;
		currentUserId?: number | null;
		depth?: number;
		documentId?: string;
		isExpanded?: boolean;
		onDeleteClick?: (event: MouseEvent) => void;
		onDeleteConfirm?: (event: MouseEvent) => void;
		onDeleteCancel?: (event: MouseEvent) => void;
		onUpdate?: (commentId: number, data: CommentUpdate) => Promise<void>;
		onCreate?: (data: CommentCreate) => Promise<void>;
	}

	let {
		comment,
		annotation = null,
		showDeleteConfirm = false,
		currentUserId = null,
		depth = 0,
		documentId = '',
		isExpanded = false,
		onDeleteClick = () => {},
		onDeleteConfirm = () => {},
		onDeleteCancel = () => {},
		onUpdate = async () => {},
		onCreate = async () => {}
	}: Props = $props();

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

	// Check if current user owns this comment
	let isOwnComment = $derived(currentUserId !== null && comment.user?.id === currentUserId);

	// Determine which replies to show
	let displayedReplies = $derived.by(() => {
		// If we've loaded replies async, use those
		if (hasLoadedReplies) {
			return loadedReplies;
		}
		// Otherwise use the comment's replies (for optimistic updates)
		return comment.replies || [];
	});

	// Show "Load more replies" button for nested comments (depth >= 1) that haven't loaded replies yet
	// Only show if we haven't already loaded replies and there are no displayed replies from backend
	let shouldShowLoadMoreButton = $derived(
		depth >= 1 && !hasLoadedReplies && !isLoadingReplies && displayedReplies.length === 0 && documentId
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
			await onUpdate(comment.id, { content: editContent.trim() });
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
			await onCreate({
				document_id: '', // Will be filled by parent
				parent_id: comment.id,
				content: replyContent.trim(),
				visibility: 'public',
				annotation: null
			});
			isReplying = false;
			replyContent = '';
			// Reload replies to show the new one
			if (depth === 0) {
				await loadReplies();
			}
		} finally {
			isSaving = false;
		}
	}

	// Load replies for this comment
	async function loadReplies() {
		if (isLoadingReplies || !documentId) return;

		isLoadingReplies = true;

		try {
			const result = await api.get<Paginated<CommentRead, never>>(`/comments?limit=50`, {
				filters: [
					{ field: 'parent_id', operator: '==', value: comment.id.toString() },
					{ field: 'document_id', operator: '==', value: documentId }
				]
			});

			if (!result.success) {
				notification(result.error);
				return;
			}

			loadedReplies = result.data.data;
			hasLoadedReplies = true;
		} catch (err) {
			console.error('Failed to load replies:', err);
		} finally {
			isLoadingReplies = false;
		}
	}

	// Load replies when comment is expanded (only at depth 0)
	$effect(() => {
		if (depth === 0 && isExpanded && !hasLoadedReplies && documentId) {
			loadReplies();
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
		<p class="text-sm font-semibold text-red-600">Delete this comment?</p>
		<div class="flex gap-2">
			<button
				onclick={onDeleteConfirm}
				disabled={isSaving}
				class="rounded-md bg-red-500 px-3 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-red-600 disabled:opacity-50"
			>
				{isSaving ? 'Deleting...' : 'Delete'}
			</button>
			<button
				onclick={onDeleteCancel}
				disabled={isSaving}
				class="rounded-md bg-gray-200 px-3 py-1.5 text-xs font-semibold text-gray-700 transition-colors hover:bg-gray-300 disabled:opacity-50"
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
				<span class="text-xs font-semibold text-gray-700">
					{comment.user?.username ?? 'Anonymous'}
				</span>
				<span class="text-xs text-gray-500">{formatDate(comment.created_at)}</span>
				{#if comment.updated_at && comment.updated_at !== comment.created_at}
					<span class="text-xs italic text-gray-400">(edited)</span>
				{/if}
			</div>
			<div class="flex gap-1">
				{#if isOwnComment && !isEditing}
					<button
						onclick={handleEditClick}
						class="rounded p-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
						aria-label="Edit comment"
						title="Edit"
					>
						<EditIcon class="h-4 w-4" />
					</button>
				{/if}
				{#if isOwnComment}
					<button
						onclick={onDeleteClick}
						class="rounded p-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-red-600"
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
			<p class="mb-2 text-xs italic text-gray-500">
				"{annotation.text.substring(0, 100)}{annotation.text.length > 100 ? '...' : ''}"
			</p>
		{/if}

		<!-- Comment content (edit mode or display) -->
		{#if isEditing}
			<div class="mb-2 flex flex-col gap-2">
				<textarea
					bind:value={editContent}
					class="min-h-16 w-full resize-none rounded border border-gray-300 bg-white p-2 text-sm text-gray-900 placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
					placeholder="Edit your comment..."
				></textarea>
				<div class="flex gap-2">
					<button
						onclick={handleSaveEdit}
						disabled={isSaving || !editContent.trim()}
						class="flex items-center gap-1 rounded bg-blue-500 px-2 py-1 text-xs font-semibold text-white transition-colors hover:bg-blue-600 disabled:opacity-50"
					>
						<SaveIcon class="h-3 w-3" />
						{isSaving ? 'Saving...' : 'Save'}
					</button>
					<button
						onclick={handleCancelEdit}
						disabled={isSaving}
						class="flex items-center gap-1 rounded bg-gray-200 px-2 py-1 text-xs font-semibold text-gray-700 transition-colors hover:bg-gray-300 disabled:opacity-50"
					>
						<CancelIcon class="h-3 w-3" />
						Cancel
					</button>
				</div>
			</div>
		{:else}
			<div class="mb-2">
				{#if comment.content}
					<p class="whitespace-pre-wrap text-sm leading-relaxed text-gray-800">
						{comment.content}
					</p>
				{:else}
					<p class="text-xs italic text-gray-400">No comment added</p>
				{/if}
			</div>

			<!-- Reply button -->
			<button
				onclick={handleReplyClick}
				class="flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-gray-600 transition-colors hover:bg-gray-100"
			>
				<ReplyIcon class="h-3 w-3" />
				Reply
			</button>
		{/if}

		<!-- Reply form -->
		{#if isReplying}
			<div class="mt-2 rounded border border-blue-300 bg-blue-50 p-2">
				<textarea
					bind:value={replyContent}
					class="mb-2 min-h-12 w-full resize-none rounded border border-gray-300 bg-white p-2 text-xs text-gray-900 placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
					placeholder="Write a reply..."
				></textarea>
				<div class="flex gap-2">
					<button
						onclick={handleSaveReply}
						disabled={isSaving || !replyContent.trim()}
						class="rounded bg-blue-500 px-2 py-1 text-xs font-semibold text-white transition-colors hover:bg-blue-600 disabled:opacity-50"
					>
						{isSaving ? 'Posting...' : 'Post Reply'}
					</button>
					<button
						onclick={handleCancelReply}
						disabled={isSaving}
						class="rounded bg-gray-200 px-2 py-1 text-xs font-semibold text-gray-700 transition-colors hover:bg-gray-300 disabled:opacity-50"
					>
						Cancel
					</button>
				</div>
			</div>
		{/if}

		<!-- Load more replies button for nested comments -->
		{#if shouldShowLoadMoreButton}
			<button
				onclick={loadReplies}
				class="mt-2 flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-blue-600 transition-colors hover:bg-blue-50"
			>
				<ExpandMoreIcon class="h-3 w-3" />
				Load replies
			</button>
		{/if}

		<!-- Loading indicator for replies -->
		{#if isLoadingReplies && !hasLoadedReplies}
			<div class="mt-3 flex items-center gap-2 text-xs text-gray-500">
				<div
					class="h-3 w-3 animate-spin rounded-full border-2 border-gray-300 border-t-blue-500"
				></div>
				Loading replies...
			</div>
		{/if}

		<!-- Recursive replies -->
		{#if displayedReplies.length > 0}
			<div class="mt-3 space-y-2 border-l-2 border-gray-200 pl-3">
				{#each displayedReplies as reply (reply.id)}
					<CommentBody
						comment={reply}
						annotation={(reply.annotation as unknown as Annotation) || null}
						showDeleteConfirm={false}
						{currentUserId}
						depth={depth + 1}
						{documentId}
						isExpanded={false}
						{onUpdate}
						{onCreate}
						onDeleteClick={(_e: MouseEvent) => {
							/* Nested deletes handled by parent */
						}}
						onDeleteConfirm={(_e: MouseEvent) => {
							/* Nested deletes handled by parent */
						}}
						onDeleteCancel={(_e: MouseEvent) => {
							/* Nested deletes handled by parent */
						}}
					/>
				{/each}
			</div>
		{/if}
	</div>
{/if}
