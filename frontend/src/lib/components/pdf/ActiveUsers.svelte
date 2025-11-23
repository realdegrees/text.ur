<script lang="ts">
	import { documentWebSocket, type ConnectedUser } from '$lib/stores/documentWebSocket';
	import { documentStore } from '$lib/runes/document.svelte.js';
	import { sessionStore } from '$lib/runes/session.svelte.js';

	interface Props {
		isExpanded?: boolean;
	}

	let { isExpanded = false }: Props = $props();

	// Get active users from store (reactive)
	let activeUsers: ConnectedUser[] = $state([]);

	// Subscribe to active users store
	$effect(() => {
		const unsubscribe = documentWebSocket.activeUsers.subscribe((users) => {
			activeUsers = users;
		});
		return unsubscribe;
	});

	// Filter out current user for display
	let otherUsers = $derived(activeUsers.filter((u) => u.user_id !== sessionStore.currentUser?.id));

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
		if (documentStore.authorFilter === userId) {
			// Toggle off if already filtering by this user
			documentStore.setAuthorFilter(null);
		} else {
			documentStore.setAuthorFilter(userId);
		}
	};

	const isFiltered = (userId: number) => documentStore.authorFilter === userId;
</script>

{#if otherUsers.length > 0}
	<div class="flex {isExpanded ? 'w-full flex-col' : 'flex-col items-center'} gap-1">
		{#if isExpanded}
			<span class="px-1 text-[10px] text-text/40">Active Users</span>
		{/if}

		{#each otherUsers.slice(0, displayLimit) as user (user.user_id)}
			<button
				class="flex items-center gap-2 rounded p-1 transition-colors hover:bg-text/10 {isFiltered(
					user.user_id
				)
					? 'ring-2 ring-primary ring-offset-1 ring-offset-background'
					: ''}"
				onclick={() => handleUserClick(user.user_id)}
				title="{user.username} - Click to filter comments"
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
