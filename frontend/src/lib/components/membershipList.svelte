<script lang="ts">
	import type { MembershipRead, UserRead } from '$api/types';
	import type { Paginated } from '$api/pagination';
	import { api } from '$api/client.js';
	import LL from '$i18n/i18n-svelte';
	import { notification } from '$lib/stores/notificationStore';
	import InfiniteScrollList from '$lib/components/infiniteScrollList.svelte';
	import CheckIcon from '~icons/material-symbols/check-circle-outline';
	import CloseIcon from '~icons/material-symbols/close-rounded';
	import { page } from '$app/state';
	import AddIcon from '~icons/material-symbols/add-circle-outline';
	import PeopleIcon from '~icons/material-symbols/group-outline';
	import DocumentIcon from '~icons/material-symbols/description-outline';
	import CrownIcon from '~icons/mdi/crown';

	interface Props {
		data: Paginated<MembershipRead, 'user'>;
		sessionUser: UserRead;
		accepted: boolean;
		compact?: boolean;
		onSelect?: (membership: Omit<MembershipRead, 'user'>) => void;
	}

	let { data, sessionUser, accepted, compact = false, onSelect }: Props = $props();

	// Get initials from group name
	function getInitials(name: string): string {
		const words = name.trim().split(/\s+/);
		if (words.length >= 2) {
			return (words[0][0] + words[1][0]).toUpperCase();
		}
		return name.slice(0, 2).toUpperCase();
	}

	/**
	 * Load more memberships with pagination.
	 */
	async function loadMore(
		offset: number,
		limit: number
	): Promise<Paginated<MembershipRead, 'user'> | undefined> {
		const result = await api.get<Paginated<MembershipRead>, 'user'>(
			`/memberships?offset=${offset}&limit=${limit}`,
			{
				filters: [
					{
						field: 'accepted',
						operator: '==',
						value: accepted.toString()
					},
					{
						field: 'user_id',
						operator: '==',
						value: sessionUser.id.toString()
					}
				]
			}
		);

		if (!result.success) {
			notification(result.error);
			return undefined;
		}

		return result.data;
	}

	/**
	 * Accept a pending group invitation.
	 */
	async function acceptInvitation(groupId: string, event: MouseEvent): Promise<void> {
		event.stopPropagation();

		const result = await api.update(`/groups/${groupId}/memberships/accept`, {});

		if (!result.success) {
			notification(result.error);
			return;
		}

		notification('success', $LL.memberships.invitationAccepted());
		window.location.reload();
	}

	/**
	 * Reject a pending group invitation.
	 */
	async function rejectInvitation(groupId: string, event: MouseEvent): Promise<void> {
		event.stopPropagation();

		const result = await api.delete(`/groups/${groupId}/memberships/reject`);

		if (!result.success) {
			notification(result.error);
			return;
		}

		notification('success', $LL.memberships.invitationRejected());
		window.location.reload();
	}

	/**
	 * Handle membership selection.
	 */
	function handleSelect(membership: Omit<MembershipRead, 'user'>): void {
		if (onSelect) {
			onSelect(membership);
		}
	}
</script>

{#if accepted}
	{#if !compact}
		<div class="flex flex-row items-center justify-between">
			<h2 class="w-full text-left text-2xl">{$LL.myGroups()}</h2>
			<a
				href="/dashboard/groups/create"
				class="flex flex-row items-center gap-1 rounded-md bg-inset px-3 py-1 text-sm shadow-inner shadow-black/30 transition-all hover:bg-green-500/20"
				title={$LL.memberships.createNewGroup()}
			>
				<AddIcon class="h-4 w-4 text-text" />
				<p class="text-text">{$LL.new()}</p>
			</a>
		</div>
		<hr class="border-text/50" />
	{/if}
	<InfiniteScrollList {data} {loadMore} step={2} onSelect={handleSelect}>
		{#snippet itemSnippet(membership: Omit<MembershipRead, 'user'>)}
			{#if compact}
				<div
					class="group m-1 flex w-full cursor-pointer items-center justify-center rounded-md bg-primary/20 py-2.5 shadow-inner shadow-black/30 transition-all hover:bg-primary"
					class:bg-primary={membership.group.id === page.params.groupid}
					class:shadow-inner-sym-[5px]={membership.group.id === page.params.groupid}
					title={membership.group.name}
				>
					<span class="text-sm font-bold text-text">{getInitials(membership.group.name)}</span>
				</div>
			{:else}
				<div
					class="group m-1 flex w-full cursor-pointer flex-col gap-2 rounded-md bg-inset px-3 py-2.5 shadow-inner shadow-black/30 transition-all hover:bg-primary"
					class:bg-primary={membership.group.id === page.params.groupid}
					class:shadow-inner-sym-[5px]={membership.group.id === page.params.groupid}
				>
					<h3 class="truncate text-left text-base font-semibold">{membership.group.name}</h3>
					<div class="flex items-center gap-3 text-xs text-text/70">
						<!-- Member count -->
						<div
							class="flex items-center gap-1"
							title={$LL.memberships.memberCount({ count: membership.group.member_count })}
						>
							<PeopleIcon class="h-4 w-4" />
							<span>{membership.group.member_count}</span>
						</div>
						<!-- Document count -->
						<div
							class="flex items-center gap-1"
							title={$LL.memberships.documentCount({ count: membership.group.document_count })}
						>
							<DocumentIcon class="h-4 w-4" />
							<span>{membership.group.document_count}</span>
						</div>
						<!-- Owner indicator -->

						<div
							class="ml-auto flex items-center"
							title={membership.is_owner ? $LL.memberships.youOwnThisGroup() : ''}
						>
							<CrownIcon
								class="h-4 w-4 {membership.is_owner ? 'text-yellow-500 hover:scale-110' : ''}"
							/>
							{#if !membership.is_owner}
								<p>{membership.group.owner?.username}</p>
							{/if}
						</div>
					</div>
				</div>
			{/if}
		{/snippet}
	</InfiniteScrollList>
{:else if data.total > 0 && !compact}
	<div class="flex flex-row items-center justify-between">
		<h2 class="w-full text-left text-xl">{$LL.invitations()}</h2>
	</div>
	<hr class="border-text/50" />
	<InfiniteScrollList {data} {loadMore} step={50}>
		{#snippet itemSnippet(invitation: Omit<MembershipRead, 'user'>)}
			<div
				class="flex w-full flex-row items-center justify-between gap-2 rounded-md bg-inset px-3 py-2.5 shadow-inner shadow-black/30"
			>
				<div class="flex min-w-0 flex-1 flex-col gap-1">
					<h4 class="truncate text-sm font-semibold">{invitation.group.name}</h4>
					<span class="truncate text-xs opacity-70">
						{invitation.group.owner?.username}
					</span>
				</div>
				<div class="flex flex-row gap-1.5">
					<button
						onclick={(e) => acceptInvitation(invitation.group.id, e)}
						class="rounded bg-green-500/30 p-1.5 shadow-inner shadow-black/30 transition-all hover:cursor-pointer hover:bg-green-500/40"
						title={$LL.memberships.acceptInvitation()}
					>
						<CheckIcon class="h-4 w-4" />
					</button>
					<button
						onclick={(e) => {
							if (confirm($LL.memberships.rejectConfirm())) {
								rejectInvitation(invitation.group.id, e);
							}
						}}
						class="rounded bg-red-500/30 p-1.5 shadow-inner shadow-black/30 transition-all hover:cursor-pointer hover:bg-red-500/40"
						title={$LL.memberships.rejectInvitation()}
					>
						<CloseIcon class="h-4 w-4" />
					</button>
				</div>
			</div>
		{/snippet}
	</InfiniteScrollList>
{/if}
