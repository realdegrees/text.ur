<script lang="ts">
	import { documentStore, type TypedComment } from '$lib/runes/document.svelte.js';
	import { sessionStore } from '$lib/runes/session.svelte.js';
	import CommentCard from './CommentCard.svelte';
	import CommentVisibility from './CommentVisibility.svelte';
	import ConfirmButton from '$lib/components/ConfirmButton.svelte';
	import MarkdownTextEditor from './MarkdownTextEditor.svelte';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import ReplyIcon from '~icons/material-symbols/reply';
	import EditIcon from '~icons/material-symbols/edit-outline';
	import DeleteIcon from '~icons/material-symbols/delete-outline';
	import CheckIcon from '~icons/material-symbols/check';
	import CloseIcon from '~icons/material-symbols/close';
	import ExpandIcon from '~icons/material-symbols/expand-more';
	import CollapseIcon from '~icons/material-symbols/expand-less';
	import { formatDateTime } from '$lib/util/dateFormat';

	interface Props {
		comment: TypedComment;
		depth?: number;
	}

	let { comment, depth = 0 }: Props = $props();

	const commentState = $derived(documentStore.comments.getState(comment.id));

	// Derived state
	let isTopLevel = $derived(depth === 0);
	let isFirstLevel = $derived(depth === 1);

	// Size classes based on depth
	let sizes = $derived({
		text: 'text-sm',
		textMuted: 'text-text/80',
		icon: 'h-3.5 w-3.5',
		iconLg: 'h-4 w-4',
		padding: 'p-2',
		buttonPx: 'px-2 py-1',
		gap: 'gap-1.5',
		mb: 'mb-3',
		mt: 'mt-1.5'
	});

	// Border colors for nested depth indication
	const borderColors = [
		'border-secondary/50',
		'border-primary/40',
		'border-green-500/40',
		'border-orange-500/40',
		'border-purple-500/40'
	];
	let borderColor = $derived(borderColors[depth % borderColors.length]);

	// State
	let isSubmitting = $state(false);
	let editContent = $derived(commentState?.editInputContent || '');
	let replyContent = $derived(commentState?.replyInputContent || '');
	let isLoadingReplies = $state(false);

	let hasUnloadedReplies = $derived(
		comment?.num_replies > 0 && (!commentState?.replies || commentState.replies.length === 0)
	);
	let isAuthor = $derived(sessionStore.currentUserId === comment?.user?.id);
	let canDeleteComment = $derived.by(() => {
		if (sessionStore.currentUserId === comment.user?.id) return true;
		return sessionStore.validatePermissions(['remove_comments']);
	});
	let canReply = $derived(
		sessionStore.routeMembership ? sessionStore.validatePermissions(['add_comments']) : false
	);

	// Handlers

	const handleReply = async () => {
		if (!replyContent.trim() || isSubmitting) return;
		isSubmitting = true;
		try {
			await documentStore.comments.create({
				content: replyContent.trim(),
				parent_id: comment.id,
				visibility: comment.visibility,
				annotation: null
			});
			documentStore.comments.setReplyInputContent(comment.id, '');
			documentStore.comments.setShowReplyInput(comment.id, false);
		} finally {
			isSubmitting = false;
		}
	};

	const handleEdit = async () => {
		if (!editContent.trim() || isSubmitting) return;
		isSubmitting = true;
		try {
			comment.content = editContent.trim();
			await documentStore.comments.update(comment);
			documentStore.comments.setEditing(comment.id, false);
		} finally {
			isSubmitting = false;
		}
	};

	const handleDeleteConfirm = async () => {
		if (isSubmitting) return;
		isSubmitting = true;
		try {
			await documentStore.comments.delete(comment.id);
		} finally {
			isSubmitting = false;
		}
	};

	const handleLoadReplies = async () => {
		if (isLoadingReplies) return;
		isLoadingReplies = true;
		try {
			await documentStore.comments.loadMoreReplies(comment.id);
		} finally {
			isLoadingReplies = false;
		}
	};

	const handleKeydown = (e: KeyboardEvent) => {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			handleReply();
		}
		if (e.key === 'Escape') {
			documentStore.comments.setShowReplyInput(comment.id, false);
			documentStore.comments.setReplyInputContent(comment.id, '');
		}
	};

	const handleEditKeydown = (e: KeyboardEvent) => {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			handleEdit();
		}
		if (e.key === 'Escape') {
			documentStore.comments.setEditing(comment.id, false);
		}
	};

	$effect(() => {
		if (commentState?.replyInputContent !== replyContent)
			documentStore.comments.setReplyInputContent(comment.id, replyContent);
	});
	$effect(() => {
		if (commentState?.editInputContent !== editContent)
			documentStore.comments.setEditInputContent(comment.id, editContent);
	});
</script>

{#snippet editDeleteButtons()}
	{#if !commentState?.isEditing && isAuthor}
		<button
			class="text-text/40 hover:bg-text/10 hover:text-text/70 rounded {isTopLevel
				? 'p-1'
				: 'p-0.5'} transition-colors"
			onclick={(e) => {
				e.stopPropagation();
				documentStore.comments.setEditing(comment.id, true);
			}}
			title="Edit"
		>
			<EditIcon class={sizes.icon} />
		</button>
	{/if}
	{#if canDeleteComment}
		<ConfirmButton onConfirm={handleDeleteConfirm} disabled={isSubmitting} slideoutDirection="left">
			{#snippet button(isOpen)}
				{#if !isOpen}
					<div
						class="text-text/40 hover:bg-text/10 hover:text-text/70 {isTopLevel
							? 'rounded-r p-0.5'
							: 'rounded p-0.5'} transition-colors"
						title="Delete"
					>
						<DeleteIcon class={sizes.icon} />
					</div>
				{:else}
					<div
						class="text-text/40 hover:text-text/70 {isTopLevel
							? 'rounded-r bg-red-500/30 hover:bg-red-500/60'
							: 'rounded bg-red-500/10 hover:bg-red-500/20'} p-0.5 transition-colors"
						title="Delete"
					>
						<CheckIcon class={sizes.icon} />
					</div>
				{/if}
			{/snippet}

			{#snippet slideout()}
				<div
					class="flex items-center gap-1 rounded {isTopLevel
						? 'rounded-l bg-red-500/10 px-2'
						: 'bg-red-500/10 px-2 py-0.5'}"
				>
					<span class="text-xs text-red-400">Delete?</span>
				</div>
			{/snippet}
		</ConfirmButton>
	{/if}
{/snippet}

<!-- Wrapper: card for top-level, border-left for nested -->
<div
	class="comment-card {borderColor}"
	class:border-l-2={!isTopLevel && !isFirstLevel}
	class:pl-2.5={!isTopLevel && !isFirstLevel}
>
	<!-- Header -->
	<!-- Header is rendered by the wrapping CommentCluster component -->

	<!-- Content area -->
	<div class={isTopLevel ? 'p-3' : ''}>
		<!-- Nested header (username + date inline) -->
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-2">
				{#if !isTopLevel}
					<span class="text-text/70 text-xs font-medium"
						>{comment.user?.username ?? 'Anonymous'}</span
					>
				{/if}
				<span class="text-text/40 text-xs">{formatDateTime(comment.created_at)}</span>
				<CommentVisibility {comment} visibility={comment.visibility} canEdit={isAuthor} />
			</div>
			{#if isAuthor || canDeleteComment}
				<div class="flex items-center gap-1">
					{@render editDeleteButtons()}
				</div>
			{/if}
		</div>

		<!-- Annotation quote (top-level only) -->
		{#if comment.annotation}
			<div class="border-primary/50 bg-primary/5 mb-3 border-l-2 py-1.5 pl-2.5 pr-2">
				<p class="text-text/60 line-clamp-2 text-xs italic">
					"{comment.annotation.text}"
				</p>
			</div>
		{/if}

		<!-- Content / Edit mode -->
		{#if commentState?.isEditing}
			<div class={sizes.mb}>
				<MarkdownTextEditor
					bind:value={editContent}
					placeholder="Edit your comment..."
					rows={3}
					disabled={isSubmitting}
					autofocus={true}
					onkeydown={handleEditKeydown}
					onblur={() => {
						if (editContent.trim().length === 0) {
							documentStore.comments.setEditing(comment.id, false);
						}
					}}
				/>
				<div class="{sizes.mt} flex justify-end {sizes.gap}">
					<button
						class="flex items-center gap-1 rounded {sizes.buttonPx} text-text/50 hover:bg-text/10 hover:text-text/70 text-xs transition-colors"
						onclick={(e) => {
							e.stopPropagation();
							documentStore.comments.setEditing(comment.id, false);
						}}
						disabled={isSubmitting}
					>
						<CloseIcon class={sizes.icon} /> Cancel
					</button>
					<button
						class="bg-primary/20 flex items-center gap-1 rounded {sizes.buttonPx} text-primary hover:bg-primary/30 text-xs font-medium transition-colors disabled:opacity-50"
						onclick={(e) => {
							e.stopPropagation();
							handleEdit();
						}}
						disabled={!editContent.trim() || isSubmitting}
					>
						<CheckIcon class={sizes.icon} />
						{isSubmitting ? 'Saving...' : 'Save'}
					</button>
				</div>
			</div>
		{:else if comment.content}
			<div class={isTopLevel ? 'mb-3' : 'mt-0.5'}>
				<MarkdownRenderer content={comment.content} class="{sizes.text} {sizes.textMuted}" />
			</div>
		{:else if isTopLevel}
			<p class="text-text/40 mb-3 text-sm italic">No comment text</p>
		{/if}

		<!-- Reply input -->
		{#if commentState?.showReplyInput}
			<div class={isTopLevel ? 'mb-3' : 'mt-2'}>
				<MarkdownTextEditor
					bind:value={replyContent}
					placeholder="Write a reply..."
					rows={2}
					disabled={isSubmitting}
					autofocus={true}
					onkeydown={handleKeydown}
					onblur={() => {
						if (replyContent.trim().length === 0) {
							documentStore.comments.setShowReplyInput(comment.id, false);
						}
					}}
				/>
				<div class="{sizes.mt} flex justify-end {sizes.gap}">
					<button
						class="rounded {sizes.buttonPx} text-text/50 hover:bg-text/10 hover:text-text/70 text-xs transition-colors"
						onclick={(e) => {
							e.stopPropagation();
							documentStore.comments.setShowReplyInput(comment.id, false);
							documentStore.comments.setReplyInputContent(comment.id, '');
						}}>Cancel</button
					>
					<button
						class="bg-primary/20 rounded {sizes.buttonPx} text-primary hover:bg-primary/30 text-xs font-medium transition-colors disabled:opacity-50"
						onclick={(e) => {
							e.stopPropagation();
							handleReply();
						}}
						disabled={!replyContent.trim() || isSubmitting}
					>
						{isSubmitting ? (isTopLevel ? 'Sending...' : '...') : 'Reply'}
					</button>
				</div>
			</div>
		{:else if canReply}
			<button
				class="{isTopLevel ? 'mb-3' : 'mt-1'} flex items-center {sizes.gap} text-xs {isTopLevel
					? 'text-primary hover:text-primary/80'
					: 'text-primary/70 hover:text-primary'} transition-colors"
				onclick={(e) => {
					e.stopPropagation();
					documentStore.comments.setShowReplyInput(comment.id, true);
				}}
			>
				<ReplyIcon class={sizes.icon} /> Reply
			</button>
		{/if}

		<!-- Load replies button -->
		{#if hasUnloadedReplies}
			<button
				class="mt-1.5 flex items-center {sizes.gap} text-text/60 hover:text-text/70 text-xs transition-colors"
				onclick={(e) => {
					e.stopPropagation();
					handleLoadReplies();
				}}
				disabled={isLoadingReplies}
			>
				<ExpandIcon class={sizes.icon} />
				{isLoadingReplies
					? 'Loading...'
					: `${comment.num_replies} ${comment.num_replies === 1 ? 'reply' : 'replies'}`}
			</button>
		{/if}

		{#if comment.num_replies > 0}
			<!-- Replies -->
			<div class={isTopLevel ? 'border-text/10 border-t pt-2' : 'mt-2'}>
				<button
					class="{isTopLevel
						? 'mb-2 w-full'
						: 'mb-1.5'} flex items-center gap-0.5 text-xs {isTopLevel
						? 'text-text/50 hover:text-text/70 font-medium'
						: 'text-text/40 hover:text-text/60'} transition-colors"
					disabled={isLoadingReplies}
					onclick={(e) => {
						e.stopPropagation();
						documentStore.comments.setRepliesCollapsed(
							comment.id,
							!commentState?.isRepliesCollapsed
						);

						if (commentState?.isRepliesCollapsed && !commentState?.replies?.length) {
							handleLoadReplies();
						}
					}}
				>
					{#if commentState?.isRepliesCollapsed}
						<ExpandIcon class={sizes.icon} />
					{:else}
						<CollapseIcon class={sizes.icon} />
					{/if}
					{commentState?.replies?.length}
					{commentState?.replies?.length === 1 ? 'reply' : 'replies'}
				</button>
				{#if !commentState?.isRepliesCollapsed}
					<div class="space-y-2">
						{#each commentState?.replies ?? [] as replyId (replyId)}
							{@const comment = documentStore.comments.getComment(replyId)}
							{#if comment}
								<CommentCard {comment} depth={depth + 1} />
							{/if}
						{/each}
					</div>
					{#if hasUnloadedReplies}
						<button
							class="mt-1.5 flex items-center {sizes.gap} text-text/60 hover:text-text/70 text-xs transition-colors"
							onclick={(e) => {
								e.stopPropagation();
								handleLoadReplies();
							}}
							disabled={isLoadingReplies}
						>
							<ExpandIcon class={sizes.icon} />
							{isLoadingReplies
								? 'Loading...'
								: `${comment.num_replies - (commentState?.replies?.length ?? 0)} more ${
										comment.num_replies - (commentState?.replies?.length ?? 0) === 1 ? 'reply' : 'replies'
									}`}
						</button>
					{/if}
				{/if}
			</div>
		{/if}
	</div>
</div>
