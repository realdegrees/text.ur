<script lang="ts">
	/**
	 * Pure presenter component for comment groups.
	 * Receives computed position from store and renders at that location.
	 */
	import type { CommentRead } from '$api/types';
	import type { Annotation } from '$types/pdf';
	import CommentBody from './CommentBody.svelte';
	import CommentConnection from './CommentConnection.svelte';
	import { fly, scale } from 'svelte/transition';
	import { quintOut } from 'svelte/easing';
	import darkModeSvelte from '$lib/stores/darkMode.svelte';

	interface Props {
		comments: CommentRead[];
		top: number;
		selectedCommentId?: number | null;
		deleteConfirmId?: number | null;
		hoverDelayMs?: number;
		expanded?: boolean;
		hovered?: boolean;
		onMouseEnter?: () => void;
		onMouseLeave?: () => void;
		onCommentSelect?: (commentId: number) => void;
		onDeleteClick?: (commentId: number, event: MouseEvent) => void;
		onDeleteConfirm?: (commentId: number, event: MouseEvent) => void;
		onDeleteCancel?: (event: MouseEvent) => void;
		onClick?: (event: MouseEvent) => void;
		sidebarRef?: HTMLDivElement | null;
		cssScaleFactor?: number;
		hoveredCommentId?: number | null;
		selectedInGroup?: number | null;
	}

	let {
		comments = [],
		top = 0,
		selectedCommentId = null,
		deleteConfirmId = null,
		hoverDelayMs = 200,
		expanded = false,
		hovered = false,
		onMouseEnter = () => {},
		onMouseLeave = () => {},
		onCommentSelect = () => {},
		onDeleteClick = () => {},
		onDeleteConfirm = () => {},
		onDeleteCancel = () => {},
		onClick = () => {},
		sidebarRef = null,
		cssScaleFactor = 1,
		hoveredCommentId = null,
		selectedInGroup = null
	}: Props = $props();

	// Separate timers for group hover handling
	let lastGroupHoverTime = $state(0);
	let groupLeaveTimer: ReturnType<typeof setTimeout> | null = $state(null);

	// Group hover handlers that respect hoverDelayMs
	function handleMouseEnter() {
		if (groupLeaveTimer) {
			clearTimeout(groupLeaveTimer);
			groupLeaveTimer = null;
		}
		lastGroupHoverTime = Date.now();
		onMouseEnter();
	}

	function handleMouseLeave() {
		const timeSinceHover = Date.now() - lastGroupHoverTime;
		const remainingDelay = Math.max(0, hoverDelayMs - timeSinceHover);

		if (remainingDelay > 0) {
			groupLeaveTimer = setTimeout(() => {
				onMouseLeave();
				groupLeaveTimer = null;
			}, remainingDelay);
		} else {
			onMouseLeave();
		}
	}

	// Active comment selection logic for group mode
	let activeComment = $derived.by(() => {
		if (selectedCommentId) {
			const found = comments.find((c) => c.id === selectedCommentId);
			return found || comments[0];
		}
		return comments[0];
	});

	// Determine active comment id used by connection (hovered in group takes precedence)
	let activeCommentId = $derived.by(() => {
		return (
			(hoveredCommentId && comments.some((c) => c.id === hoveredCommentId)
				? hoveredCommentId
				: selectedInGroup) ||
			comments[0]?.id ||
			null
		);
	});

	let activeAnnotation = $derived(activeComment?.annotation as unknown as Annotation);

	// Bindable reference to the sidebar group element
	let groupRef: HTMLElement | null = $state(null);
</script>

<!-- Connection mounted for the lifetime of the group -->
<CommentConnection
	{activeCommentId}
	{sidebarRef}
	{groupRef}
	visible={expanded || hovered}
	color={activeAnnotation?.color}
	{cssScaleFactor}
/>

{#if expanded || hovered}
	<!-- Expanded container for both group and single comment -->
	<div
		class="comment-card bg-inset absolute left-4 right-2 z-20 overflow-visible rounded-lg border-l-4 shadow-lg"
		style:top="{top}px"
		style:border-left-color={activeAnnotation?.color ?? '#ccc'}
		bind:this={groupRef}
		onmouseenter={handleMouseEnter}
		onmouseleave={handleMouseLeave}
		onclick={onClick}
		onkeydown={(e) => {
			const target = e.target as HTMLElement;
			if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') {
				return;
			}
			if (e.key === 'Enter' || e.key === ' ') {
				e.preventDefault();
				onClick(e as unknown as MouseEvent);
			}
		}}
		role="button"
		tabindex="0"
		in:fly={{ x: 20, duration: 250, easing: quintOut }}
		out:fly={{ x: 20, duration: 200, easing: quintOut }}
	>
		{#if comments.length > 1}
			<div class="border-text/10 flex flex-wrap gap-1 border-b px-3 pt-2">
				{#each comments as comment (comment.id)}
					{@const annotation = comment.annotation as unknown as Annotation}
					{@const isActive = activeComment.id === comment.id}
					<button
						class="flex items-center gap-1.5 rounded-t-md px-2.5 py-1 text-xs font-medium transition-all {isActive
							? 'bg-inset text-text border-text/20 -mb-px border-x border-t'
							: 'bg-background text-text/60'}"
						style:border-bottom={isActive ? '2px solid var(--color-inset)' : 'none'}
						onclick={(e) => {
							e.stopPropagation();
							onCommentSelect(comment.id);
						}}
					>
						<div class="h-2.5 w-2.5 rounded-full" style:background-color={annotation?.color ?? '#ccc'}></div>
						<span>{comment.user?.username?.[0]?.toUpperCase() ?? '?'}</span>
					</button>
				{/each}
			</div>
		{/if}

		<div class="px-4 py-3">
			<CommentBody
				comment={activeComment}
				annotation={activeAnnotation}
				showDeleteConfirm={deleteConfirmId === activeComment.id}
				onDeleteClick={(e) => onDeleteClick(activeComment.id, e)}
				onDeleteConfirm={(e) => onDeleteConfirm(activeComment.id, e)}
				{onDeleteCancel}
			/>
		</div>
	</div>
{:else}
	<!-- Collapsed badge for either group (count) or single (initial) -->
	{@const annotation = comments[0]?.annotation as unknown as Annotation}
	{@const badgeColor = annotation?.color ?? '#ccc'}
	<div
		class="absolute left-4 z-10 flex max-w-full justify-start"
		style:top="{top}px"
		bind:this={groupRef}
		onmouseenter={handleMouseEnter}
		onmouseleave={handleMouseLeave}
		role="button"
		tabindex="0"
		in:scale={{ duration: 200, start: 0.8, easing: quintOut }}
		out:scale={{ duration: 150, start: 0.8, easing: quintOut }}
	>
		<div
			class="cursor-pointer rounded-sm px-2 py-0.5 opacity-100 shadow-lg transition-all duration-200"
			style:background-color={badgeColor}
		>
			<span
				class="text-inset font-bold shadow-black {darkModeSvelte.enabled ? '' : 'text-shadow-lg'}"
			>
				{comments.length === 1
					? (comments[0]?.user?.username[0]?.toUpperCase() ?? '?')
					: comments.length}
			</span>
		</div>
	</div>
{/if}
