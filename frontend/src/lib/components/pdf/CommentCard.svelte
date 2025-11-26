<script lang="ts">
	import { documentStore, type CachedComment } from '$lib/runes/document.svelte.js';
	import { sessionStore } from '$lib/runes/session.svelte.js';
	import { parseAnnotation } from '$types/pdf';
	import CommentCard from './CommentCard.svelte';
	import CommentVisibility from './CommentVisibility.svelte';
	import ConfirmButton from '$lib/components/ConfirmButton.svelte';
	import MarkdownTextEditor from './MarkdownTextEditor.svelte';
	import ReplyIcon from '~icons/material-symbols/reply';
	import EditIcon from '~icons/material-symbols/edit-outline';
	import DeleteIcon from '~icons/material-symbols/delete-outline';
	import CheckIcon from '~icons/material-symbols/check';
	import CloseIcon from '~icons/material-symbols/close';
	import ExpandIcon from '~icons/material-symbols/expand-more';
	import CollapseIcon from '~icons/material-symbols/expand-less';

	interface Props {
		comments?: CachedComment[];
		activeIndex?: number;
		onSelectionChange?: (index: number) => void;
		comment?: CachedComment;
		depth?: number;
	}

	let { comments, comment, depth = 0, activeIndex = 0, onSelectionChange }: Props = $props();

	// Derived state
	let isTopLevel = $derived(depth === 0);
	let hasMultiple = $derived(isTopLevel && comments && comments.length > 1);
	let activeComment = $derived.by(() => {
		if (isTopLevel && comments) return comments[activeIndex] ?? comments[0];
		return comment!;
	});

	// Size classes based on depth
	let sizes = $derived({
		text: isTopLevel ? 'text-sm' : 'text-xs',
		textMuted: isTopLevel ? 'text-text/80' : 'text-text/60',
		icon: isTopLevel ? 'h-3.5 w-3.5' : 'h-3 w-3',
		iconLg: isTopLevel ? 'h-4 w-4' : 'h-3.5 w-3.5',
		padding: isTopLevel ? 'p-2' : 'p-1.5',
		buttonPx: isTopLevel ? 'px-2 py-1' : 'px-1.5 py-0.5',
		gap: isTopLevel ? 'gap-1.5' : 'gap-1',
		mb: isTopLevel ? 'mb-3' : 'mb-1.5',
		mt: isTopLevel ? 'mt-1.5' : 'mt-1'
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
	let showReplyInput = $state(false);
	let replyContent = $state('');
	let isSubmitting = $state(false);
	let editContent = $derived(activeComment?.content || '');
	let isLoadingReplies = $state(false);
	let isPinned = $derived.by(() => {
		return documentStore.pinnedComment?.id === activeComment?.id;
	});

	let isEditing = $derived(activeComment?.isEditing ?? false);
	let wasEdited = $derived(
		activeComment?.updated_at &&
			activeComment?.created_at &&
			activeComment.updated_at !== activeComment.created_at
	);
	let hasUnloadedReplies = $derived(
		activeComment?.num_replies > 0 && (!activeComment.replies || activeComment.replies.length === 0)
	);
	let isAuthor = $derived(sessionStore.currentUserId === activeComment?.user?.id);
	let canDeleteComment = $derived.by(() => {
		if (sessionStore.currentUserId === activeComment.user?.id) return true;
		return sessionStore.validatePermissions(['remove_comments']);
	});
	let canReply = $derived(
		sessionStore.routeMembership ? sessionStore.validatePermissions(['add_comments']) : false
	);
	let hasReplies = $derived(activeComment.replies && activeComment.replies.length > 0);

	let annotationText = $derived.by(() => {
		if (!isTopLevel || !activeComment?.annotation) return null;
		return parseAnnotation(activeComment.annotation)?.text || null;
	});

	$effect(() => {
		void activeComment?.id;
		showReplyInput = false;
		replyContent = '';
	});

	// Sync showReplyInput with store for auto-close prevention
	$effect(() => {
		if (showReplyInput && activeComment?.id) {
			documentStore.setReplyingTo(activeComment.id);
		} else if (!showReplyInput && documentStore.replyingToCommentId === activeComment?.id) {
			documentStore.setReplyingTo(null);
		}
	});

	// Handlers
	const formatDate = (dateString?: string) => {
		if (!dateString) return '';
		return new Date(dateString).toLocaleDateString(undefined, {
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	};

	const handleTabClick = (e: MouseEvent, index: number) => {
		e.stopPropagation();
		onSelectionChange?.(index);
	};

	const handleCardActivate = (e?: MouseEvent | KeyboardEvent | Event) => {
		if (!isTopLevel) return;
		// Don't capture events from interactive elements
		const target = e?.target as HTMLElement;
		if (
			target?.tagName === 'TEXTAREA' ||
			target?.tagName === 'INPUT' ||
			target?.tagName === 'BUTTON'
		)
			return;
		if (e instanceof KeyboardEvent && e.key !== 'Enter' && e.key !== ' ') return;
		if (e instanceof KeyboardEvent) e.preventDefault();
		e?.stopPropagation?.();
		if (activeComment?.id) {
			documentStore.setPinned(activeComment.id);
			documentStore.setCommentCardActive(true);
			documentStore.setSelected(activeComment.id);
		}
	};

	const handleReply = async () => {
		if (!replyContent.trim() || isSubmitting) return;
		isSubmitting = true;
		try {
			await documentStore.create({ content: replyContent.trim(), parentId: activeComment.id });
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
			await documentStore.updateComment(activeComment.id, { content: editContent.trim() });
			documentStore.setEditing(null);
		} finally {
			isSubmitting = false;
		}
	};

	const handleDeleteConfirm = async () => {
		if (isSubmitting) return;
		isSubmitting = true;
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
		if (e.key === 'Escape') documentStore.setEditing(null);
	};
</script>

<!-- Wrapper: card for top-level, border-left for nested -->
<div
	class={isTopLevel
		? `comment-card ring-primary/30 bg-background w-full rounded-lg shadow-lg shadow-black/20 ring-0 transition-all ${isPinned ? 'ring-3' : ''}`
		: `border-l-2 ${borderColor} pl-2.5`}
	role={isTopLevel ? 'button' : undefined}
	onclick={isTopLevel ? handleCardActivate : undefined}
	onkeydown={isTopLevel ? handleCardActivate : undefined}
>
	<!-- Header -->
	{#if isTopLevel}
		{#if hasMultiple && comments}
			<div class="border-text/10 flex gap-1 border-b px-2 pt-2">
				{#each comments as c, idx (c.id)}
					<button
						class="rounded-t px-2 py-1.5 text-xs font-medium transition-colors {activeIndex === idx
							? 'bg-inset text-text'
							: 'text-text/50 hover:bg-text/5 hover:text-text/70'}"
						onclick={(e) => handleTabClick(e, idx)}
						>{c.user?.username?.slice(0, 10) ?? `Comment ${idx + 1}`}</button
					>
				{/each}
			</div>
		{:else}
			<div class="border-text/10 border-b px-3 py-2">
				<span class="text-text text-sm font-semibold"
					>{activeComment.user?.username ?? 'Anonymous'}</span
				>
			</div>
		{/if}
	{/if}

	<!-- Content area -->
	<div class={isTopLevel ? 'p-3' : ''}>
		<!-- Nested header (username + date inline) -->
		{#if !isTopLevel}
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-2">
					<span class="text-text/70 text-xs font-medium"
						>{activeComment.user?.username ?? 'Anonymous'}</span
					>
					<span class="text-text/40 text-xs">{formatDate(activeComment.created_at)}</span>
					{#if isAuthor}
						<CommentVisibility
							commentId={activeComment.id}
							visibility={activeComment.visibility}
							size="sm"
						/>
					{/if}
				</div>
				{#if isAuthor}
					<div class="flex items-center gap-1">
						{#if !isEditing}
							<button
								class="text-text/40 hover:bg-text/10 hover:text-text/70 rounded p-0.5 transition-colors"
								onclick={(e) => {
									e.stopPropagation();
									documentStore.setEditing(activeComment.id);
								}}
								title="Edit"
							>
								<EditIcon class="h-3 w-3" />
							</button>
						{/if}
						<ConfirmButton
							onConfirm={handleDeleteConfirm}
							disabled={isSubmitting}
							slideoutDirection="left"
						>
							{#snippet button(isOpen)}
								{#if !isOpen}
									<div
										class="text-text/40 hover:bg-text/10 hover:text-text/70 rounded p-0.5 transition-colors"
										title="Delete"
									>
										<DeleteIcon class={sizes.icon} />
									</div>
								{:else}
									<div>
										<div
											class="text-text/40 hover:bg-text/10 hover:text-text/70 rounded p-0.5 transition-colors"
											title="Delete"
										>
											<CheckIcon class={sizes.icon} />
										</div>
									</div>
								{/if}
							{/snippet}

							{#snippet slideout()}
								<div class="flex items-center gap-1 rounded bg-red-500/10 px-2 py-0.5">
									<span class="text-xs text-red-400">Delete?</span>
								</div>
							{/snippet}
						</ConfirmButton>
					</div>
				{/if}
			</div>
		{/if}

		<!-- Annotation quote (top-level only) -->
		{#if annotationText}
			<div class="border-primary/50 bg-primary/5 mb-3 border-l-2 py-1.5 pl-2.5 pr-2">
				<p class="text-text/60 line-clamp-2 text-xs italic">"{annotationText}"</p>
			</div>
		{/if}

		<!-- Top-level meta row (date + controls) -->
		{#if isTopLevel}
			<div class="mb-2 flex items-center justify-between">
				<div class="text-text/40 flex items-center gap-2 text-xs">
					<span>{formatDate(activeComment.created_at)}</span>
					{#if wasEdited}<span
							class="italic"
							title="Last Edit: {formatDate(activeComment.updated_at)}">(edited)</span
						>{/if}
					{#if isAuthor && activeComment.visibility}
						<CommentVisibility
							commentId={activeComment.id}
							visibility={activeComment.visibility}
							size="md"
						/>
					{/if}
				</div>
				{#if canDeleteComment || isAuthor}
					<div class="flex items-center gap-1">
						{#if !isEditing && isAuthor}
							<button
								class="text-text/40 hover:bg-text/10 hover:text-text/70 rounded p-1 transition-colors"
								onclick={(e) => {
									e.stopPropagation();
									documentStore.setEditing(activeComment.id);
								}}
								title="Edit"
							>
								<EditIcon class="h-3.5 w-3.5" />
							</button>
						{/if}
						{#if canDeleteComment}
							<ConfirmButton
								onConfirm={handleDeleteConfirm}
								disabled={isSubmitting}
								slideoutDirection="left"
							>
								{#snippet button(isOpen)}
									{#if !isOpen}
										<div
											class="text-text/40 hover:bg-text/10 hover:text-text/70 rounded-r p-0.5 transition-colors"
											title="Delete"
										>
											<DeleteIcon class={sizes.icon} />
										</div>
									{:else}
										<div
											class="text-text/40 hover:text-text/70 rounded-r bg-red-500/30 p-0.5 transition-colors hover:bg-red-500/60"
											title="Delete"
										>
											<CheckIcon class={sizes.icon} />
										</div>
									{/if}
								{/snippet}

								{#snippet slideout()}
									<div class="flex items-center gap-1 rounded-l bg-red-500/10 px-2">
										<span class="text-xs text-red-400">Delete?</span>
									</div>
								{/snippet}
							</ConfirmButton>
						{/if}
					</div>
				{/if}
			</div>
		{/if}

		<!-- Content / Edit mode -->
		{#if isEditing}
			<div class={sizes.mb}>
				<MarkdownTextEditor
					bind:value={editContent}
					placeholder="Edit your comment..."
					rows={3}
					disabled={isSubmitting}
					autofocus={true}
					size={isTopLevel ? 'md' : 'sm'}
					onkeydown={handleEditKeydown}
				/>
				<div class="{sizes.mt} flex justify-end {sizes.gap}">
					<button
						class="flex items-center gap-1 rounded {sizes.buttonPx} text-text/50 hover:bg-text/10 hover:text-text/70 text-xs transition-colors"
						onclick={(e) => {
							e.stopPropagation();
							documentStore.setEditing(null);
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
		{:else if activeComment.content}
			<p class="{isTopLevel ? 'mb-3' : 'mt-0.5'} {sizes.text} {sizes.textMuted}">
				{activeComment.content}
			</p>
		{:else if isTopLevel}
			<p class="text-text/40 mb-3 text-sm italic">No comment text</p>
		{/if}

		<!-- Reply input -->
		{#if showReplyInput}
			<div class={isTopLevel ? 'mb-3' : 'mt-2'}>
				<MarkdownTextEditor
					bind:value={replyContent}
					placeholder="Write a reply..."
					rows={2}
					disabled={isSubmitting}
					autofocus={true}
					size={isTopLevel ? 'md' : 'sm'}
					onkeydown={handleKeydown}
				/>
				<div class="{sizes.mt} flex justify-end {sizes.gap}">
					<button
						class="rounded {sizes.buttonPx} text-text/50 hover:bg-text/10 hover:text-text/70 text-xs transition-colors"
						onclick={(e) => {
							e.stopPropagation();
							showReplyInput = false;
							replyContent = '';
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
					showReplyInput = true;
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
					: `${activeComment.num_replies} ${activeComment.num_replies === 1 ? 'reply' : 'replies'}`}
			</button>
		{/if}

		<!-- Replies -->
		{#if hasReplies}
			<div class={isTopLevel ? 'border-text/10 border-t pt-2' : 'mt-2'}>
				<button
					class="{isTopLevel
						? 'mb-2 w-full'
						: 'mb-1.5'} flex items-center gap-0.5 text-xs {isTopLevel
						? 'text-text/50 hover:text-text/70 font-medium'
						: 'text-text/40 hover:text-text/60'} transition-colors"
					onclick={(e) => {
						e.stopPropagation();
						documentStore.toggleRepliesCollapsed(activeComment.id);
					}}
				>
					{#if activeComment.isRepliesCollapsed}
						<ExpandIcon class={sizes.icon} />
					{:else}
						<CollapseIcon class={sizes.icon} />
					{/if}
					{activeComment.replies?.length}
					{activeComment.replies?.length === 1 ? 'reply' : 'replies'}
				</button>
				{#if !activeComment.isRepliesCollapsed}
					<div class="space-y-2">
						{#each activeComment.replies ?? [] as reply (reply.id)}
							<CommentCard comment={reply} depth={depth + 1} />
						{/each}
					</div>
				{/if}
			</div>
		{/if}
	</div>
</div>
