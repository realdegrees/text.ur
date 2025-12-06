<script lang="ts">
	import { documentStore, type TypedComment } from '$lib/runes/document.svelte.js';
	import { sessionStore } from '$lib/runes/session.svelte.js';
	import type { TagRead } from '$api/types';
	import CommentCard from './CommentCard.svelte';
	import CommentVisibility from './CommentVisibility.svelte';
	import ConfirmButton from '$lib/components/ConfirmButton.svelte';
	import MarkdownTextEditor from './MarkdownTextEditor.svelte';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import CommentTagSelector from './CommentTagSelector.svelte';
	import ReplyIcon from '~icons/material-symbols/reply';
	import EditIcon from '~icons/material-symbols/edit-outline';
	import DeleteIcon from '~icons/material-symbols/delete-outline';
	import CheckIcon from '~icons/material-symbols/check';
	import CloseIcon from '~icons/material-symbols/close';
	import ExpandIcon from '~icons/material-symbols/expand-more';
	import TagIcon from '~icons/mdi/tag-search-outline';
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
	let isLoadingReplies = $state(false);
	let editingTags = $state<TagRead[]>([]);
	let isQuoteExpanded = $state(false);
	let quoteRef: HTMLParagraphElement | null = $state(null);
	let hasQuoteOverflow = $state(false);

	let hasUnloadedReplies = $derived(
		comment?.num_replies > 0 &&
			(!commentState?.replies || commentState.replies.length - comment.num_replies < 0)
	);
	let isAuthor = $derived(sessionStore.currentUserId === comment?.user?.id);
	let canDeleteComment = $derived.by(() => {
		if (sessionStore.currentUserId === comment.user?.id) return true;
		return sessionStore.validatePermissions(['remove_comments']);
	});
	let canReply = $derived(
		sessionStore.routeMembership ? sessionStore.validatePermissions(['add_comments']) : false
	);

	// Check if content or tags have changed
	let hasChanges = $derived.by(() => {
		if (!commentState) return false;
		const contentChanged = commentState.editInputContent?.trim() !== (comment.content || '');

		// Check if tags have been added/removed
		const originalTagIds = new Set(comment.tags.map((t) => t.id));
		const editingTagIds = new Set(editingTags.map((t) => t.id));
		const tagsAddedOrRemoved =
			originalTagIds.size !== editingTagIds.size ||
			[...originalTagIds].some((id) => !editingTagIds.has(id));

		// Check if tag order has changed
		const orderChanged =
			comment.tags.length === editingTags.length &&
			comment.tags.some((tag, idx) => tag.id !== editingTags[idx]?.id);

		return contentChanged || tagsAddedOrRemoved || orderChanged;
	});

	// Handlers

	const handleReply = async () => {
		if (!commentState?.replyInputContent?.trim() || isSubmitting) return;
		isSubmitting = true;
		try {
			await documentStore.comments.create({
				content: commentState.replyInputContent.trim(),
				parent_id: comment.id,
				visibility: comment.visibility,
				annotation: null
			});
			commentState.replyInputContent = '';
			commentState.isReplying = false;
		} finally {
			isSubmitting = false;
		}
	};

	const handleEdit = async () => {
		if (!commentState) return;
		isSubmitting = true;
		try {
			comment.content = commentState.editInputContent.trim();
			await documentStore.comments.update(comment);

			// Check if tags or their order have changed
			const originalTagIds = comment.tags.map((t) => t.id);
			const editingTagIds = editingTags.map((t) => t.id);
			const tagsChanged =
				originalTagIds.length !== editingTagIds.length ||
				originalTagIds.some((id, idx) => id !== editingTagIds[idx]);

			if (tagsChanged) {
				// Remove all existing tags
				for (const tag of comment.tags) {
					await documentStore.comments.removeTag(comment.id, tag.id);
				}

				// Add tags in the new order
				for (const tag of editingTags) {
					await documentStore.comments.addTag(comment.id, tag.id);
				}
			}

			commentState.isEditing = false;
		} finally {
			isSubmitting = false;
		}
	};

	const handleCancelEdit = () => {
		if (!commentState) return;
		commentState.isEditing = false;
		commentState.editInputContent = comment.content ?? '';
		editingTags = [...comment.tags];
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
		if (e.key === 'Escape' && commentState) {
			commentState.isReplying = false;
			commentState.replyInputContent = '';
		}
	};

	const handleEditKeydown = (e: KeyboardEvent) => {
		if (e.key === 'Escape' && commentState) {
			handleCancelEdit();
		}
	};

	const handleAddTag = (tag: TagRead) => {
		if (!editingTags.find((t) => t.id === tag.id)) {
			editingTags = [...editingTags, tag];
		}
	};

	const handleRemoveTag = (tag: TagRead) => {
		editingTags = editingTags.filter((t) => t.id !== tag.id);
	};

	const availableTags = $derived(documentStore.loadedDocument?.tags ?? []);

	// Check if quote text is truncated and has overflow
	$effect(() => {
		if (quoteRef && !isQuoteExpanded) {
			// Check if content is being clamped
			hasQuoteOverflow = quoteRef.scrollHeight > quoteRef.clientHeight;
		}
	});

	// $effect(() => {
	// 	if (commentState?.replyInputContent !== replyContent)
	// 		documentStore.comments.setReplyInputContent(comment.id, replyContent);
	// });
	// $effect(() => {
	// 	if (commentState?.editInputContent !== editContent)
	// 		documentStore.comments.setEditInputContent(comment.id, editContent);
	// });
</script>

{#snippet editDeleteButtons()}
	{#if commentState && !commentState.isEditing && isAuthor}
		<button
			class="rounded text-text/40 hover:bg-text/10 hover:text-text/70 {isTopLevel
				? 'p-1'
				: 'p-0.5'} transition-colors"
			onclick={(e) => {
				e.stopPropagation();
				editingTags = [...comment.tags];
				commentState.isEditing = true;
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
	<div class={isTopLevel ? 'p-1.5' : ''}>
		<!-- Nested header (username + date inline) -->
		<div class="mb-1 flex items-center justify-between">
			<div class="flex items-center gap-2">
				{#if !isTopLevel}
					<span class="text-xs font-medium text-text/70"
						>{comment.user?.username ?? 'Anonymous'}</span
					>
				{/if}
				<span class="text-xs text-text/40">{formatDateTime(comment.created_at)}</span>
				<CommentVisibility
					{comment}
					visibility={comment.visibility}
					canEdit={isAuthor}
					{isTopLevel}
				/>
			</div>
			{#if isAuthor || canDeleteComment}
				<div class="flex items-center gap-1">
					{@render editDeleteButtons()}
				</div>
			{/if}
		</div>

		<!-- Tags section for top-level author comments -->
		{#if isTopLevel}
			{#if commentState && commentState.isEditing}
				<!-- Full tag selector when editing -->
				<div class="mb-2">
					<CommentTagSelector
						bind:selectedTags={editingTags}
						{availableTags}
						onAdd={handleAddTag}
						onRemove={handleRemoveTag}
						disabled={isSubmitting}
					/>
				</div>
			{:else if comment.tags && comment.tags.length > 0}
				<!-- Tag dots when not editing -->
				<div class="group/tags mb-2 flex w-fit flex-wrap items-center gap-1.5">
					<TagIcon class="h-4 w-4" />
					{#each comment.tags as tag (tag.id)}
						<div
							class="relative flex overflow-hidden rounded-full transition-all duration-300 ease-in-out {commentState?.isHighlightHovered
								? 'h-5 w-auto px-2 py-1'
								: 'h-2 w-2 group-hover/tags:h-5 group-hover/tags:w-auto group-hover/tags:px-2 group-hover/tags:py-1'} items-center justify-center"
						>
							<div class="absolute inset-0" style="background-color: {tag.color};"></div>
							<p
								class="relative z-10 cursor-default text-[12px] font-medium whitespace-nowrap text-text transition-opacity duration-300 {commentState?.isHighlightHovered
									? 'opacity-100'
									: 'opacity-0 group-hover/tags:opacity-100'}"
								style="text-shadow: 0 0px 4px rgba(0, 0, 0, 0.9);"
							>
								{tag.label}
							</p>
						</div>
					{/each}
				</div>
			{:else}
				<p class="mb-2 text-[11px] text-text/40 italic">No tags</p>
			{/if}
		{/if}

		<!-- Annotation quote (top-level only) -->
		{#if comment.annotation && comment.content?.length}
			<!-- svelte-ignore a11y_click_events_have_key_events -->
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<div
				class="mb-3 border-l-2 border-primary/50 bg-primary/5 py-1.5 pr-2 pl-2.5 {hasQuoteOverflow
					? 'cursor-pointer transition-colors hover:bg-primary/10'
					: ''}"
				onclick={() => {
					if (hasQuoteOverflow) {
						isQuoteExpanded = !isQuoteExpanded;
					}
				}}
			>
				<p
					bind:this={quoteRef}
					class="text-xs text-text/60 italic {isQuoteExpanded ? '' : 'line-clamp-1'}"
				>
					"{comment.annotation.text}"
				</p>
			</div>
		{/if}

		<!-- Content / Edit mode -->
		{#if commentState && commentState.isEditing}
			<div class={sizes.mb}>
				<MarkdownTextEditor
					bind:value={commentState.editInputContent}
					placeholder="Edit your comment..."
					rows={3}
					disabled={isSubmitting}
					autofocus={true}
					onkeydown={handleEditKeydown}
				/>
				<div class="{sizes.mt} flex justify-end {sizes.gap}">
					<button
						class="flex items-center gap-1 rounded {sizes.buttonPx} text-xs text-text/50 transition-colors hover:bg-text/10 hover:text-text/70"
						onclick={(e) => {
							e.stopPropagation();
							handleCancelEdit();
						}}
						disabled={isSubmitting}
					>
						<CloseIcon class={sizes.icon} /> Cancel
					</button>
					<button
						class="flex items-center gap-1 rounded bg-primary/20 {sizes.buttonPx} text-xs font-medium text-primary transition-colors hover:bg-primary/30 disabled:opacity-50"
						onclick={(e) => {
							e.stopPropagation();
							handleEdit();
						}}
						disabled={!hasChanges || isSubmitting}
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
		{/if}

		<!-- Reply input -->
		{#if commentState?.isReplying}
			<div class={isTopLevel ? 'mb-3' : 'mt-2'}>
				<MarkdownTextEditor
					bind:value={commentState.replyInputContent}
					placeholder="Write a reply..."
					rows={2}
					disabled={isSubmitting}
					autofocus={true}
					onkeydown={handleKeydown}
					onblur={() => {
						if (commentState.replyInputContent.trim().length === 0) {
							commentState.isReplying = false;
						}
					}}
				/>
				<div class="{sizes.mt} flex justify-end {sizes.gap}">
					<button
						class="rounded {sizes.buttonPx} text-xs text-text/50 transition-colors hover:bg-text/10 hover:text-text/70"
						onclick={(e) => {
							e.stopPropagation();
							commentState.isReplying = false;
							commentState.replyInputContent = '';
						}}>Cancel</button
					>
					<button
						class="rounded bg-primary/20 {sizes.buttonPx} text-xs font-medium text-primary transition-colors hover:bg-primary/30 disabled:opacity-50"
						onclick={(e) => {
							e.stopPropagation();
							handleReply();
						}}
						disabled={!commentState.replyInputContent.trim() || isSubmitting}
					>
						{isSubmitting ? (isTopLevel ? 'Sending...' : '...') : 'Reply'}
					</button>
				</div>
			</div>
		{:else if commentState && canReply}
			<button
				class="{isTopLevel ? 'mb-3' : 'mt-1'} flex items-center {sizes.gap} text-xs {isTopLevel
					? 'text-primary hover:text-primary/80'
					: 'text-primary/70 hover:text-primary'} transition-colors"
				onclick={(e) => {
					e.stopPropagation();
					commentState.isReplying = true;
				}}
			>
				<ReplyIcon class={sizes.icon} /> Reply
			</button>
		{/if}

		{#if commentState && comment.num_replies > 0}
			<!-- Replies -->
			<div class={isTopLevel ? 'border-t border-text/10 pt-2' : 'mt-2'}>
				<button
					class="{isTopLevel
						? 'mb-2 w-full'
						: 'mb-1.5'} flex items-center gap-0.5 text-xs {isTopLevel
						? 'font-medium text-text/50 hover:text-text/70'
						: 'text-text/40 hover:text-text/60'} transition-colors"
					disabled={isLoadingReplies}
					onclick={(e) => {
						e.stopPropagation();

						if (!commentState.repliesExpanded && !commentState.replies.length) {
							handleLoadReplies();
						}
						commentState.repliesExpanded = !commentState.repliesExpanded;
					}}
				>
					{#if !commentState.repliesExpanded}
						<ExpandIcon class={sizes.icon} />
						{comment.num_replies}
						{comment.num_replies === 1 ? 'reply' : 'replies'}
					{:else}
						<ExpandIcon class="{sizes.icon} rotate-180" />
						Collapse
					{/if}
				</button>
				{#if commentState.repliesExpanded}
					<div class="space-y-2">
						{#each commentState.replies ?? [] as replyId (replyId)}
							{@const comment = documentStore.comments.getComment(replyId)}
							{#if comment}
								<CommentCard {comment} depth={depth + 1} />
							{/if}
						{/each}
					</div>
					{#if hasUnloadedReplies}
						<button
							class="mt-1.5 flex items-center {sizes.gap} text-xs text-text/60 transition-colors hover:text-text/70"
							onclick={(e) => {
								e.stopPropagation();
								handleLoadReplies();
							}}
							disabled={isLoadingReplies}
						>
							<ExpandIcon class={sizes.icon} />
							{isLoadingReplies
								? 'Loading...'
								: `${comment.num_replies - (commentState.replies?.length ?? 0)} more ${
										comment.num_replies - (commentState.replies?.length ?? 0) === 1
											? 'reply'
											: 'replies'
									}`}
						</button>
					{/if}
				{/if}
			</div>
		{/if}
	</div>
</div>
