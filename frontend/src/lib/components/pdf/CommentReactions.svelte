<script lang="ts">
	import type { CommentRead, ReactionRead } from '$api/types';
	import { preciseHover } from '$lib/actions/preciseHover.js';
	import { documentStore } from '$lib/runes/document.svelte.js';
	import { sessionStore } from '$lib/runes/session.svelte.js';
	import { SvelteMap } from 'svelte/reactivity';
	import RemoveIcon from '~icons/material-symbols/close-rounded';

	interface Props {
		comment: CommentRead;
	}

	let { comment }: Props = $props();

	// Group reactions by group_reaction_id
	let groupedReactions = $derived.by(() => {
		const groups = new SvelteMap<number, ReactionRead[]>();
		for (const reaction of comment.reactions) {
			const existing = groups.get(reaction.group_reaction_id) ?? [];
			existing.push(reaction);
			groups.set(reaction.group_reaction_id, existing);
		}
		return groups;
	});

	// Find the current user's reaction (if any)
	let myReaction = $derived(
		comment.reactions.find((r) => r.user.id === sessionStore.currentUserId)
	);

	// Whether the current user is the comment author (cannot react to own comment)
	let isAuthor = $derived(sessionStore.currentUserId === comment.user?.id);

	let isSubmitting = $state(false);

	// --- Hover popup state ---
	let hoveredGroupReactionId = $state<number | null>(null);
	let popupPos = $state<{ x: number; y: number }>({ x: 0, y: 0 });
	let badgeHovered = $state(false);
	let popupHovered = $state(false);

	const canRemoveReactions = $derived(sessionStore.validatePermissions(['remove_reactions']));

	// Close popup when neither badge nor popup is hovered.
	// preciseHover processes all registrations in a single rAF pass, so
	// badge onLeave and popup onEnter fire synchronously in the same call.
	// Deferring the close check to the next rAF guarantees both flags are
	// settled — this is deterministic, not timer-based.
	let closeRafId: number | null = null;
	const scheduleClose = () => {
		if (closeRafId !== null) cancelAnimationFrame(closeRafId);
		closeRafId = requestAnimationFrame(() => {
			closeRafId = null;
			if (!badgeHovered && !popupHovered) {
				hoveredGroupReactionId = null;
			}
		});
	};

	// Svelte action wrapper that creates preciseHover params for a badge.
	// The action receives the DOM node directly from `use:`, so we can
	// read getBoundingClientRect inside onEnter.
	function badgePreciseHover(node: HTMLElement, groupReactionId: number) {
		const makeParams = (id: number) => ({
			onEnter: () => {
				badgeHovered = true;
				const rect = node.getBoundingClientRect();
				// 1px overlap: badge (z-50) paints over popup (z-40) top border at seam
				popupPos = { x: rect.left, y: rect.bottom - 1 };
				hoveredGroupReactionId = id;
			},
			onLeave: () => {
				badgeHovered = false;
				scheduleClose();
			}
		});

		const action = preciseHover(node, makeParams(groupReactionId));
		return {
			destroy: action.destroy,
			update(newId: number) {
				action.update(makeParams(newId));
			}
		};
	}

	const popupHoverParams = {
		onEnter: () => {
			popupHovered = true;
		},
		onLeave: () => {
			popupHovered = false;
			scheduleClose();
		}
	};

	const handleReactionClick = async (groupReactionId: number) => {
		if (isSubmitting || isAuthor) return;
		isSubmitting = true;
		try {
			if (myReaction?.group_reaction_id === groupReactionId) {
				await documentStore.comments.removeReaction(comment.id);
			} else {
				await documentStore.comments.addReaction(comment.id, groupReactionId);
			}
		} finally {
			isSubmitting = false;
		}
	};

	const handleRemoveUserReaction = async (userId: number) => {
		if (isSubmitting) return;
		isSubmitting = true;
		try {
			await documentStore.comments.removeReactionByUser(comment.id, userId);
		} finally {
			isSubmitting = false;
		}
	};
</script>

{#if groupedReactions.size > 0}
	<div class="relative flex items-center gap-1">
		{#each [...groupedReactions.entries()] as [groupReactionId, reactions] (groupReactionId)}
			{@const isOpen = hoveredGroupReactionId === groupReactionId}
			{@const firstReaction = reactions[0]}
			<button
				class="flex cursor-pointer items-center gap-0.5 px-1.5 py-0.5 text-xs transition-colors
					{isOpen
					? 'z-50 rounded-t rounded-b-none border border-b-0 border-text/20 bg-inset'
					: myReaction?.group_reaction_id === groupReactionId
						? 'rounded-full bg-primary/20 ring-1 ring-primary/50'
						: 'rounded-full bg-text/5 hover:bg-text/10'}"
				onclick={(e) => {
					e.stopPropagation();
					handleReactionClick(groupReactionId);
				}}
				use:badgePreciseHover={groupReactionId}
				disabled={isSubmitting || isAuthor}
			>
				<span class="text-[13px] leading-[1]">{firstReaction.emoji}</span>
				<span class="text-[11px] leading-[1] text-text/70 tabular-nums">{reactions.length}</span>
			</button>
		{/each}
	</div>

	<!-- Hover popup: flush below badge, merges visually into one element -->
	{#if hoveredGroupReactionId && groupedReactions.has(hoveredGroupReactionId)}
		{@const reactions = groupedReactions.get(hoveredGroupReactionId)!}
		<div
			class="fixed z-40 w-max rounded-tl-none rounded-tr-md rounded-b-md border border-text/20 bg-inset px-2 py-1.5 shadow-xl"
			style="left: {popupPos.x}px; top: {popupPos.y}px;"
			use:preciseHover={popupHoverParams}
		>
			{#each reactions as reaction (reaction.user.id)}
				<div class="flex items-center justify-between gap-2 py-0.5">
					<span class="truncate text-xs text-text/80">{reaction.user.username}</span>
					{#if canRemoveReactions}
						<button
							class="flex-shrink-0 cursor-pointer text-text/30 transition-colors hover:text-red-500"
							onclick={(e) => {
								e.stopPropagation();
								handleRemoveUserReaction(reaction.user.id);
							}}
							disabled={isSubmitting}
							title="Remove reaction"
						>
							<RemoveIcon class="h-3.5 w-3.5" />
						</button>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
{/if}
