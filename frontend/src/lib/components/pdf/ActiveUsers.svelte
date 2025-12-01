<script lang="ts">
	import { documentWebSocket } from '$lib/stores/documentWebSocket.svelte';
	import { documentStore, type AuthorFilterState } from '$lib/runes/document.svelte';
	import PersonIcon from '~icons/material-symbols/person';
	import { sessionStore } from '$lib/runes/session.svelte';
	import RemoveIcon from '~icons/material-symbols/remove';
	import EyeOpen from '~icons/mdi/eye';
	import EyeClosed from '~icons/mdi/eye-off';

	interface Props {
		isExpanded?: boolean;
	}

	let { isExpanded = false }: Props = $props();

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
		hoveredUserId = null; // Reset hover state on click to not show the hover icon immediately which would be confusing
	};
	let hoveredUserId = $state<number | null>(null);
</script>

{#snippet filterStateElement(hovered: boolean, filterState?: AuthorFilterState)}
	{#if filterState === 'include'}
		{#if hovered}
			<div title="Hide highlights by this user" class="opacity-40">
				<EyeClosed />
			</div>
		{:else}
			<div>
				<EyeOpen />
			</div>
		{/if}
	{:else if filterState === 'exclude'}
		{#if hovered}
			<div title="Clear Filter" class="opacity-40">
				<RemoveIcon />
			</div>
		{:else}
			<div>
				<EyeClosed />
			</div>
		{/if}
	{:else if hovered}
		<div title="Include highlights by this user" class="opacity-40">
			<EyeOpen />
		</div>
	{/if}
{/snippet}

{#if documentWebSocket.activeUsers.length > 0}
	<div class="flex flex-col {!isExpanded && 'items-center'} h-full w-full gap-2 overflow-y-auto">
		<!--Header if expanded-->
		{#if isExpanded}
			<span class="px-1 text-[10px] text-text/40">Active Users</span>
		{/if}

		<!--Clear filters button-->
		<button
			class="flex items-center justify-center gap-2 rounded bg-primary/50 px-0 text-primary {isExpanded
				? 'w-full px-2 text-left'
				: ''}"
			onclick={() => documentStore.filters.clearAuthorFilter()}
			disabled={documentStore.filters.authorFilters.size === 0}
		>
			{#if isExpanded}
				{documentStore.filters.authorFilters.size === 0 ? 'No filters' : 'Clear filters'}
			{:else}
				<RemoveIcon class="h-7 w-7" />
			{/if}
		</button>

		<!--Scrollable List of active users-->
		<div
			class="flex h-full w-full flex-col {isExpanded
				? 'justify-between'
				: 'items-center'} gap-3 overflow-y-auto"
		>
			{#each documentWebSocket.activeUsers as user (user.user_id)}
				{@const filterState = documentStore.filters.authorFilters.get(user.user_id)}
				{@const hovered = hoveredUserId === user.user_id}
				{@const isSessionUser = user.user_id === sessionStore.currentUser?.id}
				<button
					class="flex cursor-pointer items-center justify-between gap-2 rounded text-text/70"
					onclick={() => handleUserClick(user.user_id)}
					title="{user.username} - Click to cycle include → exclude → none"
					onmouseenter={() => (hoveredUserId = user.user_id)}
					onmouseleave={() => (hoveredUserId = null)}
				>
					<div class="flex flex-row items-center gap-2">
						<div class="relative">
							{#if isSessionUser}
								<PersonIcon class="h-7 w-7 shrink-0 rounded-full text-text/70" />
							{:else}
								<div
									class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[11px] font-medium text-text {getUserColor(
										user.user_id
									)}"
								>
									{getInitials(user.username)}
								</div>
							{/if}
							{#if !isExpanded}
								<div
									class="absolute -top-1 left-0.5 flex h-3 w-3 items-center justify-center rounded-full p-0.5"
								>
									{@render filterStateElement(hovered, filterState)}
								</div>
							{/if}
						</div>
						{#if isExpanded}
							<span class="truncate text-xs text-text/70"
								>{user.username} {isSessionUser ? '(You)' : ''}</span
							>
						{/if}
					</div>
					{#if isExpanded}
						{@render filterStateElement(hovered, filterState)}
					{/if}
				</button>
			{/each}
		</div>
	</div>
{:else if isExpanded}
	<span class="px-1 text-[10px] text-text/40">No other users viewing</span>
{/if}
