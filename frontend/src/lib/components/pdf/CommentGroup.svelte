<script lang="ts">
	import type { CommentRead, CommentCreate, CommentUpdate } from '$api/types';
	import type { Annotation } from '$types/pdf';
	import CommentBody from './CommentBody.svelte';
	import { fly, scale } from 'svelte/transition';
	import { quintOut } from 'svelte/easing';

	interface Props {
		comments: CommentRead[];
		top: number;
		isGroupExpanded: boolean;
		isGroupHovered: boolean;
		selectedCommentId?: number | null;
		deleteConfirmId: number | null;
		currentUserId?: number | null;
		documentId?: string;
		hoverDelayMs?: number;
		onGroupClick?: (event: MouseEvent) => void;
		onGroupMouseEnter?: () => void;
		onGroupMouseLeave?: () => void;
		onCommentSelect?: (commentId: number) => void;
		onDeleteClick?: (commentId: number, event: MouseEvent) => void;
		onDeleteConfirm?: (commentId: number, event: MouseEvent) => void;
		onDeleteCancel?: (event: MouseEvent) => void;
		onUpdate?: (commentId: number, data: CommentUpdate) => Promise<void>;
		onCreate?: (data: CommentCreate) => Promise<void>;
	}

	let {
		comments = [],
		top,
		isGroupExpanded,
		isGroupHovered,
		selectedCommentId = null,
		deleteConfirmId,
		currentUserId = null,
		documentId = '',
		hoverDelayMs = 200,
		onGroupClick = () => {},
		onGroupMouseEnter = () => {},
		onGroupMouseLeave = () => {},
		onCommentSelect = () => {},
		onDeleteClick = () => {},
		onDeleteConfirm = () => {},
		onDeleteCancel = () => {},
		onUpdate = async () => {},
		onCreate = async () => {}
	}: Props = $props();

	let lastHoverTime = $state(0);
	let leaveTimer: ReturnType<typeof setTimeout> | null = $state(null);

	function handleGroupMouseEnter() {
		// Clear any pending leave timer
		if (leaveTimer) {
			clearTimeout(leaveTimer);
			leaveTimer = null;
		}
		lastHoverTime = Date.now();
		onGroupMouseEnter();
	}

	function handleGroupMouseLeave() {
		const timeSinceHover = Date.now() - lastHoverTime;
		const remainingDelay = Math.max(0, hoverDelayMs - timeSinceHover);

		if (remainingDelay > 0) {
			// Delay the leave event
			leaveTimer = setTimeout(() => {
				onGroupMouseLeave();
				leaveTimer = null;
			}, remainingDelay);
		} else {
			// No delay needed
			onGroupMouseLeave();
		}
	}

	// If no comment is selected, default to first comment
	let activeComment = $derived.by(() => {
		if (selectedCommentId) {
			const found = comments.find((c) => c.id === selectedCommentId);
			return found || comments[0];
		}
		return comments[0];
	});

	let activeAnnotation = $derived(activeComment.annotation as unknown as Annotation);
</script>

{#if isGroupExpanded || isGroupHovered}
	<!-- Expanded view with tabs -->
	<div
		class="absolute right-2 left-4 z-20 overflow-visible rounded-lg border-l-4 bg-white shadow-lg"
		style:top="{top}px"
		style:border-left-color={activeAnnotation.color}
		onmouseenter={handleGroupMouseEnter}
		onmouseleave={handleGroupMouseLeave}
		onclick={onGroupClick}
		onkeydown={(e) => {
			if (e.key === 'Enter' || e.key === ' ') {
				e.preventDefault();
				onGroupClick(e as any);
			}
		}}
		role="button"
		tabindex="0"
		in:fly={{ x: -20, duration: 250, easing: quintOut }}
		out:fly={{ x: -20, duration: 200, easing: quintOut }}
	>
		<!-- Tabs row -->
		{#if comments.length > 1}
			<div class="flex flex-wrap gap-1 border-b border-gray-200 px-3 pt-2">
				{#each comments as comment (comment.id)}
					{@const annotation = comment.annotation as unknown as Annotation}
					{@const isActive = activeComment.id === comment.id}
					<button
						class="flex items-center gap-1.5 rounded-t-md px-2.5 py-1 text-xs font-medium transition-all"
						class:bg-gray-100={!isActive}
						class:text-gray-600={!isActive}
						class:bg-white={isActive}
						class:text-gray-900={isActive}
						class:border-t={isActive}
						class:border-x={isActive}
						class:border-gray-300={isActive}
						class:-mb-px={isActive}
						style:border-bottom={isActive ? '2px solid white' : 'none'}
						onclick={(e) => {
							e.stopPropagation();
							onCommentSelect(comment.id);
						}}
					>
						<div class="h-2.5 w-2.5 rounded-full" style:background-color={annotation.color}></div>
						<span>{comment.user?.username?.[0]?.toUpperCase() ?? '?'}</span>
					</button>
				{/each}
			</div>
		{/if}

		<!-- Active comment content -->
		<div class="px-4 py-3">
			<CommentBody
				comment={activeComment}
				annotation={activeAnnotation}
				showDeleteConfirm={deleteConfirmId === activeComment.id}
				{currentUserId}
				{documentId}
				isExpanded={isGroupExpanded}
				onDeleteClick={(e) => onDeleteClick(activeComment.id, e)}
				onDeleteConfirm={(e) => onDeleteConfirm(activeComment.id, e)}
				{onDeleteCancel}
				{onUpdate}
				{onCreate}
			/>
		</div>
	</div>
{:else}
	<!-- Collapsed indicators that can wrap -->
	<div
		class="absolute right-2 left-4 z-10 flex max-w-full flex-wrap justify-end gap-1"
		style:top="{top}px"
		onmouseenter={handleGroupMouseEnter}
		onmouseleave={handleGroupMouseLeave}
		onclick={onGroupClick}
		onkeydown={(e) => {
			if (e.key === 'Enter' || e.key === ' ') {
				e.preventDefault();
				onGroupClick(e as any);
			}
		}}
		role="button"
		tabindex="0"
		in:scale={{ duration: 200, start: 0.8, easing: quintOut }}
		out:scale={{ duration: 150, start: 0.8, easing: quintOut }}
	>
		{#each comments as comment (comment.id)}
			{@const annotation = comment.annotation as unknown as Annotation}
			<div
				class="cursor-pointer rounded-full px-2.5 py-1 shadow-md transition-all duration-200 hover:scale-105 hover:shadow-lg"
				style:background-color={annotation.color}
				title={comment.user?.username ?? 'Anonymous'}
			>
				<span class="text-xs font-semibold text-gray-800">
					{comment.user?.username?.[0]?.toUpperCase() ?? '?'}
				</span>
			</div>
		{/each}
	</div>
{/if}
