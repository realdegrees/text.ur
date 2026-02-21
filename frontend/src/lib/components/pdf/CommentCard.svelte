<script lang="ts">
	import { documentStore } from '$lib/runes/document.svelte.js';
	import { sessionStore } from '$lib/runes/session.svelte.js';
	import LL from '$i18n/i18n-svelte';
	import type { CommentRead, TagRead } from '$api/types';
	import CommentCard from './CommentCard.svelte';
	import CommentVisibility from './CommentVisibility.svelte';
	import ConfirmButton from '$lib/components/ConfirmButton.svelte';
	import MarkdownTextEditor from './MarkdownTextEditor.svelte';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import CommentTagSelector from './CommentTagSelector.svelte';
	import CommentReactions from './CommentReactions.svelte';
	import ReplyIcon from '~icons/material-symbols/reply';
	import EditIcon from '~icons/material-symbols/edit-outline';
	import DeleteIcon from '~icons/material-symbols/delete-outline';
	import CheckIcon from '~icons/material-symbols/check';
	import CloseIcon from '~icons/material-symbols/close';
	import ExpandIcon from '~icons/material-symbols/expand-more';
	import TagIcon from '~icons/mdi/tag-search-outline';
	import AddReactionIcon from '~icons/material-symbols/add-reaction-outline';
	import { formatDateTime } from '$lib/util/dateFormat';
	import { env } from '$env/dynamic/public';

	interface Props {
		comment: CommentRead;
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
		mb: 'mb-2',
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
	let isReactionPickerOpen = $state(false);
	let isReactionSubmitting = $state(false);
	let reactionButtonRef = $state<HTMLButtonElement | null>(null);
	let pickerPos = $derived.by(() => {
		if (!reactionButtonRef || !isReactionPickerOpen) return { top: 0, left: 0 };
		const rect = reactionButtonRef.getBoundingClientRect();
		return { top: rect.top, left: rect.right };
	});

	// Dynamic group reactions from store (sorted by order)
	let availableReactions = $derived(
		[...documentStore.groupReactions].sort((a, b) => a.order - b.order)
	);

	let myReaction = $derived(
		comment.reactions?.find((r) => r.user.id === sessionStore.currentUserId)
	);

	const handlePickerReaction = async (groupReactionId: number) => {
		if (isReactionSubmitting || isAuthor) return;
		isReactionSubmitting = true;
		try {
			if (myReaction?.group_reaction_id === groupReactionId) {
				await documentStore.comments.removeReaction(comment.id);
			} else {
				await documentStore.comments.addReaction(comment.id, groupReactionId);
			}
		} finally {
			isReactionSubmitting = false;
			isReactionPickerOpen = false;
		}
	};

	let hasUnloadedReplies = $derived(
		comment?.num_replies > 0 &&
			(!commentState?.replies || commentState.replies.length - comment.num_replies < 0)
	);
	let isAuthor = $derived(sessionStore.currentUserId === comment?.user?.id);
	let canDeleteComment = $derived.by(() => {
		if (sessionStore.currentUserId === comment.user?.id) return true;
		return sessionStore.validatePermissions(['administrator']);
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
				// Update tags in a single operation
				await documentStore.comments.updateTags(comment.id, editingTagIds);
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
</script>

{#snippet actionButtons()}
	<!-- Add reaction button (top-level only, hidden when no reactions configured) -->
	{#if isTopLevel && !isAuthor && availableReactions.length > 0}
		<button
			bind:this={reactionButtonRef}
			class="flex cursor-pointer items-center rounded bg-text/5 p-1 text-text/40 transition-colors hover:bg-text/10 hover:text-text/60"
			title={$LL.comments.addReaction()}
			onclick={(e) => {
				e.stopPropagation();
				isReactionPickerOpen = !isReactionPickerOpen;
			}}
			disabled={isReactionSubmitting}
		>
			<AddReactionIcon class="h-3.5 w-3.5" />
		</button>
	{/if}

	{#if commentState && canReply && !commentState.isReplying}
		<button
			class="flex items-center gap-1 rounded bg-primary/10 px-1.5 py-0.5 text-[11px] font-medium text-primary transition-colors hover:bg-primary/20"
			onclick={(e) => {
				e.stopPropagation();
				commentState.isReplying = true;
			}}
			title={$LL.reply()}
		>
			<ReplyIcon class="h-3 w-3" />
			<span>{$LL.reply()}</span>
		</button>
	{/if}
	{#if commentState && !commentState.isEditing && isAuthor}
		<button
			class="flex items-center rounded bg-text/5 p-1 text-text/60 transition-colors hover:bg-text/10 hover:text-text/80"
			onclick={(e) => {
				e.stopPropagation();
				editingTags = [...comment.tags];
				commentState.isEditing = true;
			}}
			title={$LL.edit()}
		>
			<EditIcon class="h-3.5 w-3.5" />
		</button>
	{/if}
	{#if canDeleteComment}
		<ConfirmButton onConfirm={handleDeleteConfirm} disabled={isSubmitting} slideoutDirection="left">
			{#snippet button(isOpen)}
				{#if !isOpen}
					<div
						class="flex cursor-pointer items-center rounded bg-orange-500/10 p-1 text-orange-600 transition-colors hover:bg-orange-500/20 hover:text-orange-700"
						title={$LL.delete()}
					>
						<DeleteIcon class="h-3.5 w-3.5" />
					</div>
				{:else}
					<div
						class="flex cursor-pointer items-center rounded bg-orange-500/20 p-1 text-orange-600 transition-colors hover:bg-orange-500/30"
						title={$LL.comments.confirmDelete()}
					>
						<CheckIcon class="h-3.5 w-3.5" />
					</div>
				{/if}
			{/snippet}

			{#snippet slideout()}
				<!-- Slideout content if needed, though button itself handles confirmation state mostly -->
				<div class="flex items-center gap-1 rounded bg-orange-500/10 px-2 py-0.5">
					<span class="text-xs text-orange-600">{$LL.comments.deleteConfirm()}</span>
				</div>
			{/snippet}
		</ConfirmButton>
	{/if}
{/snippet}

{#snippet expandButton()}
	{#if commentState && comment.num_replies > 0}
		<button
			class="flex items-center gap-0.5 text-xs {isTopLevel
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
				{$LL.comments.nReplies({ count: comment.num_replies })}
			{:else}
				<ExpandIcon class="{sizes.icon} rotate-180" />
				{$LL.collapse()}
			{/if}
		</button>
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
	<div class={isTopLevel ? 'p-1' : ''}>
		<!-- Nested header (username + date inline) -->
		<div class="mb-1 flex items-center justify-between gap-2">
			<div class="flex items-center gap-2">
				{#if !isTopLevel}
					<span class="text-xs font-medium text-text/70"
						>{comment.user?.username ?? $LL.anonymous()}</span
					>
				{/if}
				<span class="text-xs text-text/40">{formatDateTime(comment.created_at)}</span>
				<CommentVisibility
					{comment}
					visibility={comment.visibility}
					canEdit={isAuthor}
					{isTopLevel}
				/>

				<!-- Tags inline with header for top-level comments -->
				{#if isTopLevel && commentState && !commentState.isEditing}
					{#if comment.tags && comment.tags.length > 0}
						<div class="flex items-center gap-1">
							<TagIcon class="h-3.5 w-3.5" />
							{#each comment.tags as tag (tag.id)}
								<div
									class="relative flex h-4 w-auto items-center justify-center overflow-hidden rounded-full px-1.5 py-0.5"
								>
									<div class="absolute inset-0" style="background-color: {tag.color};"></div>
									<p
										class="relative z-10 cursor-default text-[11px] font-medium whitespace-nowrap text-text"
										style="text-shadow: 0 0px 4px rgba(0, 0, 0, 0.9);"
									>
										{tag.label}
									</p>
								</div>
							{/each}
						</div>
					{/if}
				{/if}
			</div>

			<!-- Action Buttons (Reply, Edit, Delete) -->
			<div class="flex items-center gap-1.5">
				{@render actionButtons()}
			</div>
		</div>

		<!-- Tags section for editing mode only -->
		{#if isTopLevel && commentState && commentState.isEditing}
			<div class="mb-1.5">
				<CommentTagSelector
					bind:selectedTags={editingTags}
					{availableTags}
					onAdd={handleAddTag}
					onRemove={handleRemoveTag}
					disabled={isSubmitting}
				/>
			</div>
		{/if}

		<!-- Annotation quote (top-level only) -->
		{#if comment.annotation && comment.content?.length}
			<!-- svelte-ignore a11y_click_events_have_key_events -->
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<div
				class="mb-2 border-l-2 border-primary/50 bg-primary/5 py-1 pr-2 pl-2.5 {hasQuoteOverflow
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
					placeholder={$LL.comments.editPlaceholder()}
					rows={3}
					disabled={isSubmitting}
					maxCommentLength={env.PUBLIC_MAX_COMMENT_LENGTH
						? parseInt(env.PUBLIC_MAX_COMMENT_LENGTH)
						: 2000}
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
						<CloseIcon class={sizes.icon} /> {$LL.cancel()}
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
						{isSubmitting ? $LL.saving() : $LL.save()}
					</button>
				</div>
			</div>
		{:else if comment.content}
			<div class={isTopLevel ? 'mb-1' : 'mt-0.5'}>
				<MarkdownRenderer content={comment.content} class="{sizes.text} {sizes.textMuted}" />
			</div>
		{/if}

		<!-- Action Bar: Expand + Reactions -->
		{#if isTopLevel || (!commentState?.isReplying && comment.num_replies > 0)}
			<div class="flex items-center gap-3 {isTopLevel ? 'mt-1 mb-1' : 'mt-1'}">
				{#if !commentState?.isReplying && comment.num_replies > 0}
					{@render expandButton()}
				{/if}
				{#if isTopLevel}
					<CommentReactions {comment} />
				{/if}
			</div>
		{/if}

		<!-- Reply input -->
		{#if commentState?.isReplying}
			<div class={isTopLevel ? 'mb-2' : 'mt-2'}>
				<MarkdownTextEditor
					bind:value={commentState.replyInputContent}
					placeholder={$LL.comments.replyPlaceholder()}
					rows={2}
					disabled={isSubmitting}
					autofocus={true}
					maxCommentLength={env.PUBLIC_MAX_COMMENT_LENGTH
						? parseInt(env.PUBLIC_MAX_COMMENT_LENGTH)
						: 2000}
					onkeydown={handleKeydown}
					onblur={() => {
						if (commentState.replyInputContent.trim().length === 0) {
							commentState.isReplying = false;
						}
					}}
				/>
				<div class="{sizes.mt} flex justify-end {sizes.gap}">
					<!-- Show expand button here too so context isn't lost -->
					<div class="mr-auto">
						{@render expandButton()}
					</div>

					<button
						class="rounded {sizes.buttonPx} text-xs text-text/50 transition-colors hover:bg-text/10 hover:text-text/70"
						onclick={(e) => {
							e.stopPropagation();
							commentState.isReplying = false;
						commentState.replyInputContent = '';
					}}>{$LL.cancel()}</button
					>
					<button
						class="rounded bg-primary/20 {sizes.buttonPx} text-xs font-medium text-primary transition-colors hover:bg-primary/30 disabled:opacity-50"
						onclick={(e) => {
							e.stopPropagation();
							handleReply();
						}}
						disabled={!commentState.replyInputContent.trim() || isSubmitting}
					>
						{isSubmitting ? $LL.comments.sending() : $LL.reply()}
					</button>
				</div>
			</div>
		{/if}

		<!-- Replies List (only if expanded) -->
		{#if commentState && comment.num_replies > 0 && commentState.repliesExpanded}
			<div class={isTopLevel ? 'border-t border-text/10 pt-1.5' : 'mt-1.5'}>
				<div class="space-y-1.5">
					{#each commentState.replies ?? [] as replyId (replyId)}
						{@const comment = documentStore.comments.getComment(replyId)}
						{#if comment}
							<CommentCard {comment} depth={depth + 1} />
						{/if}
					{/each}
				</div>
				{#if hasUnloadedReplies}
					<button
						class="mt-1 flex items-center {sizes.gap} text-xs text-text/60 transition-colors hover:text-text/70"
						onclick={(e) => {
							e.stopPropagation();
							handleLoadReplies();
						}}
						disabled={isLoadingReplies}
					>
						<ExpandIcon class={sizes.icon} />
					{isLoadingReplies
						? $LL.loading()
						: $LL.comments.nMoreReplies({ count: comment.num_replies - (commentState.replies?.length ?? 0) })}
					</button>
				{/if}
			</div>
		{/if}
	</div>
</div>

<!-- Reaction picker popup (rendered outside card to escape overflow clipping) -->
{#if isReactionPickerOpen}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<div class="fixed inset-0 z-[100]" onclick={() => (isReactionPickerOpen = false)}>
		<div
			class="fixed z-[101] flex items-center gap-0.5 rounded-lg bg-inset p-1 shadow-xl ring-1 ring-text/20"
			style="top: {pickerPos.top}px; left: {pickerPos.left}px; transform: translate(-100%, -100%) translateY(-4px);"
			onclick={(e) => e.stopPropagation()}
		>
			{#each availableReactions as gr (gr.id)}
				<button
					class="cursor-pointer rounded-md p-1 text-base transition-colors hover:bg-text/10
					{myReaction?.group_reaction_id === gr.id ? 'bg-primary/20 ring-1 ring-primary/50' : ''}"
					title={$LL.comments.nPoints({ count: gr.points })}
					onclick={(e) => {
						e.stopPropagation();
						handlePickerReaction(gr.id);
					}}
					disabled={isReactionSubmitting}
				>
					{gr.emoji}
				</button>
			{/each}
		</div>
	</div>
{/if}
