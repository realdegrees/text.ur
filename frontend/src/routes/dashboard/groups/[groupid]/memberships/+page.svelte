<script lang="ts">
	import InfiniteTable from '$lib/components/infiniteScrollTable.svelte';
	import type { GroupMembershipRead, Permission } from '$api/types';
	import OwnerIcon from '~icons/material-symbols/admin-panel-settings-outline';
	import PendingIcon from '~icons/material-symbols/pending-outline';
	import AcceptedIcon from '~icons/material-symbols/check-circle-outline';
	import { permissionSchema } from '$api/schemas';
	import LL from '$i18n/i18n-svelte.js';
	import { api } from '$api/client.js';
	import type { Paginated } from '$api/pagination.js';

	let { data } = $props();
	let memberships = $derived(data.memberships);
	let group = $derived(data.group);

	let selected = $state<GroupMembershipRead[]>([]);

	// Handle selection changes
	function handleSelectionChange(memberships: GroupMembershipRead[]) {
		selected = memberships;
		console.log('Selected memberships:', memberships.length);
	}

	// Available permissions for adding
	const availablePermissions = permissionSchema.options.map((p) => p.value);
</script>

<div class="h-screen p-4">
	<h1 class="mb-4 text-2xl font-bold">Member Management</h1>

	{#if selected.length > 0}
		<div class="mb-4 rounded bg-blue-50 p-3">
			<p class="text-sm font-medium">
				{selected.length} member{selected.length === 1 ? '' : 's'} selected
			</p>
		</div>
	{/if}

	<InfiniteTable
		columns={[
			{
				label: $LL.user(),
				width: '1fr',
				snippet: usernameSnippet
			},
			{
				label: $LL.status(),
				width: '1fr',
				snippet: badgeSnippet
			},
			{
				label: $LL.permissions.label(),
				width: '5fr',
				snippet: permissionsSnippet
			}
		]}
		data={memberships}
		loadMore={(offset, limit) =>
			api.fetch<Paginated<GroupMembershipRead>>(
				`/groups/${group?.id}/memberships?offset=${offset}&limit=${limit}`,
				{
					sort: [{ field: 'accepted', direction: 'asc' }]
				}
			)}
		step={20}
		selectable={true}
		onSelectionChange={handleSelectionChange}
		rowBgClass="bg-inset/90"
	/>
</div>

{#snippet usernameSnippet(membership: GroupMembershipRead)}
	<div class="flex flex-row items-center text-text">
		<p class="font-medium">{membership.user.username || 'Unknown User'}</p>
		{#if membership.user.first_name || membership.user.last_name}
			<p class="ml-1 text-text/70">
				({membership.user.first_name || ''}
				{membership.user.last_name || ''})
			</p>
		{/if}
	</div>
{/snippet}

{#snippet badgeSnippet(membership: GroupMembershipRead)}
	<span
		class="flex w-fit flex-row rounded-full px-2 py-1 text-xs font-semibold uppercase"
		class:bg-blue-100={membership.is_owner}
		class:text-blue-800={membership.is_owner}
		class:bg-green-100={membership.accepted}
		class:text-green-800={membership.accepted}
		class:bg-yellow-100={!membership.accepted}
		class:text-yellow-800={!membership.accepted}
	>
		{#if membership.is_owner}
			<OwnerIcon class="mr-1 inline h-4 w-4 align-text-bottom" />
			{$LL.group.memberships.owner()}
		{:else if membership.accepted}
			<AcceptedIcon class="mr-1 inline h-4 w-4 align-text-bottom" />
			{$LL.group.memberships.accepted()}
		{:else}
			<PendingIcon class="mr-1 inline h-4 w-4 align-text-bottom" />
			{$LL.group.memberships.invited()}
		{/if}
	</span>
{/snippet}

{#snippet permissionsSnippet(membership: GroupMembershipRead)}
	<div class="flex flex-wrap items-center gap-1">
		{#each membership.permissions as perm (perm)}
			<span
				class="inline-flex items-center gap-1 rounded bg-gray-100 px-2 py-1 text-xs text-gray-700"
			>
				{perm}
				<button
					onclick={() => {
						// TODO remove permission via API call
					}}
					class="font-bold text-red-600 hover:text-red-800"
					aria-label="Remove {perm} permission"
				>
					x
				</button>
			</span>
		{/each}

		<select
			class="cursor-pointer rounded border border-gray-300 bg-white px-2 py-1 text-xs hover:bg-gray-50"
			onchange={(e) => {
				const newPerm = e.currentTarget.value as Permission;
				if (newPerm && !membership.permissions.includes(newPerm)) {
					// TODO add permission via API call
				}
				e.currentTarget.value = '';
			}}
		>
			<option value="">+ {$LL.add()}</option>
			{#each availablePermissions.filter((p) => !membership.permissions.includes(p)) as perm (perm)}
				<option value={perm}>{perm}</option>
			{/each}
		</select>
	</div>
{/snippet}
