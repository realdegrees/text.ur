<script lang="ts">
	import { documentWebSocket } from '$lib/stores/documentWebSocket.svelte';
	import { documentStore } from '$lib/runes/document.svelte';
	import PersonIcon from '~icons/material-symbols/person';
	import { sessionStore } from '$lib/runes/session.svelte';
	import RemoveIcon from '~icons/material-symbols/remove';

	interface Props {
		isExpanded?: boolean;
	}

	let { isExpanded = false }: Props = $props();

	// Show current user first (if present) and the rest afterwards
	let currentUserId = $derived(sessionStore.currentUser?.id);
	let currentConnection = $derived(
		documentWebSocket.activeUsers.find((u) => u.user_id === currentUserId)
	);
	let otherUsers = $derived(
		documentWebSocket.activeUsers.filter((u) => u.user_id !== currentUserId)
	);
	// Check if filters should be disabled (restricted mode without view_restricted_comments permission)
	let isRestrictedWithoutPermission = $derived(
		documentStore.loadedDocument?.view_mode === 'restricted' &&
			!sessionStore.validatePermissions(['view_restricted_comments'])
	);

	// Show more users when expanded
	let displayLimit = $derived(isExpanded ? 10 : 3);

	// Get initials from username
	const getInitials = (username: string): string => {
		return username.slice(0, 2).toUpperCase();
	};

	// Generate a consistent color based on user ID
	const getUserColor = (userId: number): string => {
		const colors = [
			'bg-blue-500',
			'bg-green-500',
			'bg-purple-500',
			'bg-orange-500',
			'bg-pink-500',
			'bg-teal-500',
			'bg-indigo-500',
			'bg-rose-500'
		];
		return colors[userId % colors.length];
	};

	const handleUserClick = (userId: number) => {
		documentStore.filters.toggleAuthorFilter(userId);
	};

	// Button styling to match PdfControls
	const buttonClass =
		'flex items-center gap-2 rounded p-1 text-text/70 transition-colors hover:bg-text/10 hover:text-text';
	const activeButtonClass =
		'flex items-center gap-2 rounded text-primary bg-primary/10 transition-colors hover:bg-primary/20';

	/** Get the filter state for a user: 'include', 'exclude' or undefined (none) */
	type AuthorFilterState = 'include' | 'exclude';
	const getFilterState = (userId: number): AuthorFilterState | undefined =>
		documentStore.filters.authorFilters.get(userId);
</script>

{#if currentConnection || otherUsers.length > 0}
	<div class="flex {isExpanded ? 'w-full flex-col' : 'flex-col items-center'} gap-2">
		{#if isExpanded}
			<span class="px-1 text-[10px] text-text/40">Active Users</span>

			{#if documentStore.filters.authorFilters.size > 0 && !isRestrictedWithoutPermission}
				<button
					class="{activeButtonClass} {isExpanded ? 'w-full px-2 text-left' : ''}"
					onclick={() => documentStore.filters.clearAuthorFilter()}
				>
					Clear filters
				</button>
			{/if}
		{/if}

		{#if documentStore.filters.authorFilters.size > 0 && !isRestrictedWithoutPermission && !isExpanded}
			<button
				class="{activeButtonClass} p-2"
				onclick={() => documentStore.filters.clearAuthorFilter()}
				title="Clear filters"
			>
				<RemoveIcon class="h-4 w-4" />
			</button>
		{/if}

		{#if currentConnection}
			<!-- Session user shown first with PersonIcon and same click behavior -->
			<button
				class="{buttonClass} {getFilterState(currentConnection.user_id) === 'include'
					? 'ring-2 ring-green-500/70'
					: getFilterState(currentConnection.user_id) === 'exclude'
						? 'ring-2 ring-red-500/70'
						: ''} justify-start"
				onclick={() => handleUserClick(currentConnection.user_id)}
				title="{currentConnection.username} - Click to cycle include → exclude → none"
			>
				<PersonIcon class="h-7 w-7 shrink-0 text-text/70" />
				{#if isExpanded}
					<span class="truncate text-xs text-text/70">{currentConnection.username} (you)</span>
				{/if}
			</button>
		{/if}

		{#each otherUsers.slice(0, displayLimit - (currentConnection ? 1 : 0)) as user (user.user_id)}
			<button
				class="{buttonClass} {getFilterState(user.user_id) === 'include'
					? 'ring-2 ring-green-500/70'
					: getFilterState(user.user_id) === 'exclude'
						? 'ring-2 ring-red-500/70'
						: ''}"
				onclick={() => handleUserClick(user.user_id)}
				title="{user.username} - Click to cycle include → exclude → none"
			>
				<div
					class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[10px] font-medium text-white {getUserColor(
						user.user_id
					)}"
				>
					{getInitials(user.username)}
				</div>
				{#if isExpanded}
					<span class="truncate text-xs text-text/70">{user.username}</span>
				{/if}
			</button>
		{/each}

		<!-- Show count if more than display limit -->
		{#if otherUsers.length > displayLimit}
			<div
				class="flex {isExpanded
					? 'items-center gap-2 p-1'
					: ''} h-7 w-7 items-center justify-center rounded-full bg-text/30 text-[10px] font-medium text-text"
				title="{otherUsers.length - displayLimit} more users viewing"
			>
				{#if isExpanded}
					<span>+{otherUsers.length - displayLimit} more</span>
				{:else}
					+{otherUsers.length - displayLimit}
				{/if}
			</div>
		{/if}
	</div>
{:else if isExpanded}
	<span class="px-1 text-[10px] text-text/40">No other users viewing</span>
{/if}
