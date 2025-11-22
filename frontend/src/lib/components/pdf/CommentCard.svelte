<script lang="ts">
	import { documentStore, type CachedComment } from '$lib/runes/document.svelte.js';
	import { sessionStore } from '$lib/runes/session.svelte.js';
	import { parseAnnotation } from '$types/pdf';
	import CommentCard from './CommentCard.svelte';
	import DeleteIcon from '~icons/material-symbols/delete-outline';
	import ReplyIcon from '~icons/material-symbols/reply';
	import EditIcon from '~icons/material-symbols/edit-outline';
	import CheckIcon from '~icons/material-symbols/check';
	import CloseIcon from '~icons/material-symbols/close';
	import ExpandIcon from '~icons/material-symbols/expand-more';

	interface Props {
		// For clustered top-level comments (depth=0)
		comments?: CachedComment[];
		activeIndex?: number;
		onSelectionChange?: (index: number) => void;
		// For single comment / replies (depth > 0)
		comment?: CachedComment;
		depth?: number;
	}

	let {
		comments,
		comment,
		depth = 0,
		activeIndex = 0,
		onSelectionChange
	}: Props = $props();

	// Determine which comment to display
	let isTopLevel = $derived(depth === 0);
	let hasMultiple = $derived(isTopLevel && comments && comments.length > 1);
	let activeComment = $derived.by(() => {
		if (isTopLevel && comments) {
			return comments[activeIndex] ?? comments[0];
		}
		return comment!;
	});

	// Max depth for visual indentation
	const MAX_INDENT_DEPTH = 4;

	// State
	let showReplyInput = $state(false);
	let replyContent = $state('');
	let isSubmitting = $state(false);
	let editContent = $state('');
	let isLoadingReplies = $state(false);
	let showDeleteConfirm = $state(false);
	let deleteConfirmRef: HTMLDivElement | null = $state(null);

	// Derive isEditing from the comment's flag
	let isEditing = $derived(activeComment?.isEditing ?? false);

	// When entering edit mode, populate the edit content
	$effect(() => {
		if (isEditing) {
			editContent = activeComment?.content || '';
		} else {
			editContent = '';
		}
	});

	// Reset other local state when active comment changes
	$effect(() => {
		void activeComment?.id;
		showReplyInput = false;
		replyContent = '';
		showDeleteConfirm = false;
	});

	// Close delete confirmation when clicking outside
	$effect(() => {
		if (!showDeleteConfirm) return;

		const handleClickOutside = (e: MouseEvent) => {
			if (deleteConfirmRef && !deleteConfirmRef.contains(e.target as Node)) {
				showDeleteConfirm = false;
			}
		};

		// Use setTimeout to avoid the click that opened the confirm from immediately closing it
		// Use capture phase to catch clicks before stopPropagation prevents bubbling
		const timeoutId = setTimeout(() => {
			document.addEventListener('click', handleClickOutside, true);
		}, 0);

		return () => {
			clearTimeout(timeoutId);
			document.removeEventListener('click', handleClickOutside, true);
		};
	});

	// Handle tab click for clustered comments
	const handleTabClick = (index: number) => {
		onSelectionChange?.(index);
	};

	// Pin the comment when activating the card (only for top-level)
	const handleCardActivate = (e?: MouseEvent | KeyboardEvent | Event) => {
		if (!isTopLevel) return;

		if (e instanceof KeyboardEvent) {
			if (e.key !== 'Enter' && e.key !== ' ') return;
			e.preventDefault();
		}

		e?.stopPropagation?.();

		const commentId = activeComment?.id;
		if (commentId) {
			documentStore.setPinned(commentId);
			documentStore.setCommentCardActive(true);
			documentStore.setSelected(commentId);
		}
	};

	// Parse the annotation to get the highlighted text (top-level only)
	let annotationText = $derived.by(() => {
		if (!isTopLevel || !activeComment?.annotation) return null;
		const parsed = parseAnnotation(activeComment.annotation);
		return parsed?.text || null;
	});

	// Check if the comment was edited
	let wasEdited = $derived(
		activeComment?.updated_at &&
			activeComment?.created_at &&
			activeComment.updated_at !== activeComment.created_at
	);

	// Check if replies need to be loaded
	let hasUnloadedReplies = $derived(
		activeComment?.num_replies > 0 &&
			(!activeComment.replies || activeComment.replies.length === 0)
	);

	// Check if user can modify/delete this comment
	let canModifyComment = $derived(
		sessionStore.canModifyComment(activeComment?.user?.id ?? null)
	);

	const formatDate = (dateString?: string) => {
		if (!dateString) return '';
		const date = new Date(dateString);
		return date.toLocaleDateString(undefined, {
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	};

	const handleReply = async () => {
		if (!replyContent.trim() || isSubmitting) return;
		isSubmitting = true;
		try {
			await documentStore.create({
				content: replyContent.trim(),
				parentId: activeComment.id
			});
			replyContent = '';
			showReplyInput = false;
		} finally {
			isSubmitting = false;
		}
	};

	const handleEdit = async () => {
		if (!editContent.trim() || isSubmitting) return;
		isSubmitting = true;
		try {
			await documentStore.updateComment(activeComment.id, {
				content: editContent.trim()
			});
			documentStore.setEditing(null);
		} finally {
			isSubmitting = false;
		}
	};

	const handleDeleteClick = () => {
		showDeleteConfirm = true;
	};

	const handleDeleteConfirm = async () => {
		if (isSubmitting) return;
		isSubmitting = true;
		showDeleteConfirm = false;
		try {
			await documentStore.deleteComment(activeComment.id);
		} finally {
			isSubmitting = false;
		}
	};

	const handleLoadReplies = async () => {
		if (isLoadingReplies) return;
		isLoadingReplies = true;
		try {
			await documentStore.loadReplies(activeComment.id);
		} finally {
			isLoadingReplies = false;
		}
	};

	const startEditing = () => {
		documentStore.setEditing(activeComment.id);
	};

	const cancelEditing = () => {
		documentStore.setEditing(null);
	};

	const handleKeydown = (e: KeyboardEvent) => {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			handleReply();
		}
		if (e.key === 'Escape') {
			showReplyInput = false;
			replyContent = '';
		}
	};

	const handleEditKeydown = (e: KeyboardEvent) => {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			handleEdit();
		}
		if (e.key === 'Escape') {
			cancelEditing();
		}
	};

	// Border colors for reply depth indication
	const borderColors = [
		'border-secondary/50',
		'border-primary/40',
		'border-green-500/40',
		'border-orange-500/40',
		'border-purple-500/40'
	];
	let borderColor = $derived(borderColors[depth % borderColors.length]);
</script>

{#if isTopLevel}
	<!-- Top-level comment card -->
	<div
		class="comment-card w-full rounded-lg border border-text/10 bg-background shadow-lg shadow-black/20"
		role="button"
		tabindex="0"
		onclick={handleCardActivate}
		onkeydown={handleCardActivate}
	>
		<!-- Tabs for multiple clustered comments, or username for single -->
		{#if hasMultiple && comments}
			<div class="flex gap-1 border-b border-text/10 px-2 pt-2">
				{#each comments as c, idx (c.id)}
					<button
						class="rounded-t px-2 py-1.5 text-xs font-medium transition-colors {activeIndex ===
						idx
							? 'bg-inset text-text'
							: 'text-text/50 hover:bg-text/5 hover:text-text/70'}"
						onclick={() => handleTabClick(idx)}
					>
						{c.user?.username?.slice(0, 10) ?? `Comment ${idx + 1}`}
					</button>
				{/each}
			</div>
		{:else}
			<div class="border-b border-text/10 px-3 py-2">
				<span class="text-sm font-semibold text-text">
					{activeComment.user?.username ?? 'Anonymous'}
				</span>
			</div>
		{/if}

		<div class="p-3">
			<!-- Annotation quote -->
			{#if annotationText}
				<div
					class="mb-3 border-l-2 border-primary/50 bg-primary/5 py-1.5 pl-2.5 pr-2"
				>
					<p class="line-clamp-2 text-xs italic text-text/60">
						"{annotationText}"
					</p>
				</div>
			{/if}

			<!-- Timestamp and controls in same row -->
			<div class="mb-2 flex items-center justify-between">
				<div class="flex items-center gap-2 text-xs text-text/40">
					<span>{formatDate(activeComment.created_at)}</span>
					{#if wasEdited}
						<span class="italic" title="Last Edit: {formatDate(activeComment.updated_at)}">(edited)</span>
					{/if}
				</div>
				<div class="flex items-center gap-1">
					{#if canModifyComment}
						{#if !isEditing}
							<button
								class="rounded p-1 text-text/40 transition-colors hover:bg-text/10 hover:text-text/70"
								onclick={startEditing}
								title="Edit comment"
							>
								<EditIcon class="h-3.5 w-3.5" />
							</button>
						{/if}
						<div class="relative" bind:this={deleteConfirmRef}>
							{#if showDeleteConfirm}
								<div class="flex items-center gap-1 rounded bg-red-500/10 px-1.5 py-0.5">
									<span class="text-xs text-red-400">Delete?</span>
									<button
										class="rounded p-0.5 text-red-400 transition-colors hover:bg-red-500/20 hover:text-red-500"
										onclick={handleDeleteConfirm}
										title="Confirm delete"
										disabled={isSubmitting}
									>
										<CheckIcon class="h-3.5 w-3.5" />
									</button>
								</div>
							{:else}
								<button
									class="rounded p-1 text-text/40 transition-colors hover:bg-red-500/20 hover:text-red-500"
									onclick={handleDeleteClick}
									title="Delete comment"
									disabled={isSubmitting}
								>
									<DeleteIcon class="h-3.5 w-3.5" />
								</button>
							{/if}
						</div>
					{/if}
				</div>
			</div>

			<!-- Content -->
			{#if isEditing}
				<div class="mb-3">
					<textarea
						class="w-full resize-none rounded border border-text/20 bg-inset p-2 text-sm text-text placeholder:text-text/40 focus:border-primary focus:outline-none"
						placeholder="Edit your comment..."
						rows="3"
						bind:value={editContent}
						onkeydown={handleEditKeydown}
						disabled={isSubmitting}
					></textarea>
					<div class="mt-1.5 flex justify-end gap-1.5">
						<button
							class="flex items-center gap-1 rounded px-2 py-1 text-xs text-text/50 transition-colors hover:bg-text/10 hover:text-text/70"
							onclick={cancelEditing}
							disabled={isSubmitting}
						>
							<CloseIcon class="h-3.5 w-3.5" />
							Cancel
						</button>
						<button
							class="flex items-center gap-1 rounded bg-primary/20 px-2 py-1 text-xs font-medium text-primary transition-colors hover:bg-primary/30 disabled:opacity-50"
							onclick={handleEdit}
							disabled={!editContent.trim() || isSubmitting}
						>
							<CheckIcon class="h-3.5 w-3.5" />
							{isSubmitting ? 'Saving...' : 'Save'}
						</button>
					</div>
				</div>
			{:else if activeComment.content}
				<p class="mb-3 text-sm text-text/80">{activeComment.content}</p>
			{:else}
				<p class="mb-3 text-sm italic text-text/40">No comment text</p>
			{/if}

			<!-- Reply input / button -->
			{#if showReplyInput}
				<div class="mb-3">
					<textarea
						class="w-full resize-none rounded border border-text/20 bg-inset p-2 text-sm text-text placeholder:text-text/40 focus:border-primary focus:outline-none"
						placeholder="Write a reply..."
						rows="2"
						bind:value={replyContent}
						onkeydown={handleKeydown}
						disabled={isSubmitting}
					></textarea>
					<div class="mt-1.5 flex justify-end gap-1.5">
						<button
							class="rounded px-2 py-1 text-xs text-text/50 transition-colors hover:bg-text/10 hover:text-text/70"
							onclick={() => {
								showReplyInput = false;
								replyContent = '';
							}}
						>
							Cancel
						</button>
						<button
							class="rounded bg-primary/20 px-2 py-1 text-xs font-medium text-primary transition-colors hover:bg-primary/30 disabled:opacity-50"
							onclick={handleReply}
							disabled={!replyContent.trim() || isSubmitting}
						>
							{isSubmitting ? 'Sending...' : 'Reply'}
						</button>
					</div>
				</div>
			{:else}
				<button
					class="mb-3 flex items-center gap-1.5 text-xs text-primary transition-colors hover:text-primary/80"
					onclick={() => (showReplyInput = true)}
				>
					<ReplyIcon class="h-4 w-4" />
					Reply
				</button>
			{/if}

			<!-- Load replies button -->
			{#if hasUnloadedReplies}
				<button
					class="mb-3 flex w-full items-center justify-center gap-1.5 rounded border border-text/10 bg-inset/50 py-1.5 text-xs text-text/60 transition-colors hover:bg-inset hover:text-text/80"
					onclick={handleLoadReplies}
					disabled={isLoadingReplies}
				>
					<ExpandIcon class="h-4 w-4" />
					{isLoadingReplies
						? 'Loading...'
						: `Load ${activeComment.num_replies} ${activeComment.num_replies === 1 ? 'reply' : 'replies'}`}
				</button>
			{/if}

			<!-- Replies (recursive) -->
			{#if activeComment.replies && activeComment.replies.length > 0}
				<div class="space-y-2 border-t border-text/10 pt-2">
					<span class="text-xs font-medium text-text/50">
						{activeComment.replies.length}
						{activeComment.replies.length === 1 ? 'reply' : 'replies'}
					</span>
					{#each activeComment.replies as reply (reply.id)}
						<CommentCard comment={reply} depth={1} />
					{/each}
				</div>
			{/if}
		</div>
	</div>
{:else}
	<!-- Reply (nested comment) -->
	<div class="border-l-2 {borderColor} pl-2.5 {depth < MAX_INDENT_DEPTH ? '' : 'ml-0'}">
		<!-- Reply header -->
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-2">
				<span class="text-xs font-medium text-text/70">
					{activeComment.user?.username ?? 'Anonymous'}
				</span>
				<span class="text-xs text-text/40">
					{formatDate(activeComment.created_at)}
				</span>
			</div>
			<div class="flex items-center gap-1">
				{#if canModifyComment}
					<div class="relative" bind:this={deleteConfirmRef}>
						{#if showDeleteConfirm}
							<div class="flex items-center gap-1 rounded bg-red-500/10 px-1 py-0.5">
								<span class="text-xs text-red-400">Delete?</span>
								<button
									class="rounded p-0.5 text-red-400 transition-colors hover:bg-red-500/20 hover:text-red-500"
									onclick={handleDeleteConfirm}
									title="Confirm delete"
									disabled={isSubmitting}
								>
									<CheckIcon class="h-3 w-3" />
								</button>
							</div>
						{:else}
							<button
								class="rounded p-0.5 text-text/30 transition-colors hover:bg-red-500/20 hover:text-red-500"
								onclick={handleDeleteClick}
								title="Delete reply"
								disabled={isSubmitting}
							>
								<DeleteIcon class="h-3 w-3" />
							</button>
						{/if}
					</div>
				{/if}
			</div>
		</div>

		<!-- Reply content -->
		<p class="mt-0.5 text-xs text-text/60">{activeComment.content}</p>

		<!-- Load nested replies button -->
		{#if hasUnloadedReplies}
			<button
				class="mt-1.5 flex items-center gap-1 text-xs text-text/50 transition-colors hover:text-text/70"
				onclick={handleLoadReplies}
				disabled={isLoadingReplies}
			>
				<ExpandIcon class="h-3.5 w-3.5" />
				{isLoadingReplies
					? 'Loading...'
					: `${activeComment.num_replies} ${activeComment.num_replies === 1 ? 'reply' : 'replies'}`}
			</button>
		{/if}

		<!-- Reply input toggle -->
		{#if showReplyInput}
			<div class="mt-2">
				<textarea
					class="w-full resize-none rounded border border-text/20 bg-inset p-1.5 text-xs text-text placeholder:text-text/40 focus:border-primary focus:outline-none"
					placeholder="Write a reply..."
					rows="2"
					bind:value={replyContent}
					onkeydown={handleKeydown}
					disabled={isSubmitting}
				></textarea>
				<div class="mt-1 flex justify-end gap-1">
					<button
						class="rounded px-1.5 py-0.5 text-xs text-text/50 transition-colors hover:bg-text/10 hover:text-text/70"
						onclick={() => {
							showReplyInput = false;
							replyContent = '';
						}}
					>
						Cancel
					</button>
					<button
						class="rounded bg-primary/20 px-1.5 py-0.5 text-xs font-medium text-primary transition-colors hover:bg-primary/30 disabled:opacity-50"
						onclick={handleReply}
						disabled={!replyContent.trim() || isSubmitting}
					>
						{isSubmitting ? '...' : 'Reply'}
					</button>
				</div>
			</div>
		{:else}
			<button
				class="mt-1 flex items-center gap-1 text-xs text-primary/70 transition-colors hover:text-primary"
				onclick={() => (showReplyInput = true)}
			>
				<ReplyIcon class="h-3 w-3" />
				Reply
			</button>
		{/if}

		<!-- Nested replies (recursive) -->
		{#if activeComment.replies && activeComment.replies.length > 0}
			<div class="mt-2 space-y-2">
				{#each activeComment.replies as nestedReply (nestedReply.id)}
					<CommentCard comment={nestedReply} depth={depth + 1} />
				{/each}
			</div>
		{/if}
	</div>
{/if}
