<script lang="ts">
	import InfiniteTable from '$lib/components/infiniteScrollTable.svelte';
	import type {
		MembershipCreate,
		MembershipPermissionUpdate,
		MembershipRead,
		Permission,
		UserRead
	} from '$api/types';
	import OwnerIcon from '~icons/material-symbols/admin-panel-settings-outline';
	import PendingIcon from '~icons/material-symbols/pending-outline';
	import AcceptedIcon from '~icons/material-symbols/check-circle-outline';
	import RemoveIcon from '~icons/material-symbols/close-rounded';
	import AddIcon from '~icons/material-symbols/add-2-rounded';
	import { permissionSchema } from '$api/schemas';
	import LL from '$i18n/i18n-svelte.js';
	import { api } from '$api/client.js';
	import type { Paginated } from '$api/pagination.js';
	import { validatePermissions } from '$api/validatePermissions.js';
	import { notification } from '$lib/stores/notificationStore.js';
	import Dropdown from '$lib/components/dropdown.svelte';
	import { scale, slide } from 'svelte/transition';
	import AdvancedInput from '$lib/components/advancedInput.svelte';
	import { invalidateAll } from '$app/navigation';

	let { data } = $props();
	let memberships = $derived(data.memberships);
	let group = $derived(data.membership.group);
	console.log(data.membership);

	let selected = $state<Omit<MembershipRead, 'group'>[]>([]);
	let username = $state('');
	let selectedUser = $state<UserRead | undefined>(undefined);

	const availablePermissions = permissionSchema.options.map((p) => p.value);

	function handleSelectionChange(memberships: Omit<MembershipRead, 'group'>[]) {
		selected = memberships;
		console.log('Selected memberships:', memberships.length);
	}

	async function updateMembershipPermissions(
		userId: number,
		permissions: Permission[]
	): Promise<boolean> {
		const result = await api.update(`/groups/${group.id}/memberships/${userId}/permissions`, {
			permissions
		} satisfies MembershipPermissionUpdate);

		if (!result.success) {
			notification(result.error);
			return false;
		}
		return true;
	}

	async function addPermissionToMembership(
		membership: Omit<MembershipRead, 'group'>,
		permission: Permission
	): Promise<void> {
		if (membership.permissions.includes(permission)) return;

		const newPermissions = [...membership.permissions, permission];
		const success = await updateMembershipPermissions(membership.user.id, newPermissions);
		if (success) {
			membership.permissions = newPermissions;
		}
	}

	async function removePermissionFromMembership(
		membership: Omit<MembershipRead, 'group'>,
		permission: Permission
	): Promise<void> {
		if (!membership.permissions.includes(permission)) return;

		const newPermissions = membership.permissions.filter((p) => p !== permission);
		const success = await updateMembershipPermissions(membership.user.id, newPermissions);
		if (success) {
			membership.permissions = newPermissions;
		}
	}

	async function leaveGroup(): Promise<boolean> {
		const result = await api.delete(`/groups/${group.id}/memberships/reject`);
		if (!result.success) {
			notification(result.error);
			return false;
		}
		return true;
	}
	async function kickMember(userId: number): Promise<boolean> {
		const result = await api.delete(`/groups/${group.id}/memberships/${userId}`);
		if (!result.success) {
			notification(result.error);
			return false;
		}
		return true;
	}

	async function fetchUserOptions(search: string): Promise<UserRead[]> {
		const response = await api.get<Paginated<UserRead>>(`/users`, {
			filters: [
				{ field: 'username', operator: 'ilike', value: search },
				{ field: 'group_id', operator: '!=', value: group.id }
			]
		});
		if (response.success) {
			console.log(response.data);
			return response.data.data;
		}
		return [];
	}

	function handleInviteSubmit() {
		if (selectedUser) {
			api
				.post(`/groups/${group.id}/memberships`, {
					user_id: selectedUser.id
				} satisfies MembershipCreate)
				.then((result) => {
					if (result.success) {
						notification('success', 'User invited successfully!');
						username = '';
						selectedUser = undefined;
					} else {
						notification(result.error);
					}
				});
		}
	}
</script>

<div class="h-screen p-4">
	<div class="mb-4 flex w-full flex-row items-center justify-between gap-2">
		<h1 class="text-2xl font-bold">Member Management</h1>
		{#if validatePermissions(data.membership, ['add_members'])}
			<!--INVITE-->
			<div class="flex flex-row items-end gap-2">
				<div class="w-64">
					<AdvancedInput
						fetchOptions={fetchUserOptions}
						bind:value={username}
						bind:selected={selectedUser}
						config={{ placeholder: 'Search username...' }}
						stringify={{
							option: (user) => `${user.username}`,
							hint: (s) => ` (${s?.first_name || ''} ${s?.last_name || ''})`
						}}
						onSubmit={handleInviteSubmit}
					/>
				</div>
				<button
					class="rounded bg-green-500/30 px-3 py-2.5 font-semibold shadow-inner shadow-black/30 transition hover:cursor-pointer hover:bg-green-500/40"
					onclick={handleInviteSubmit}
					disabled={!selectedUser}
					class:opacity-50={!selectedUser}
					class:cursor-not-allowed={!selectedUser}>Invite</button
				>
			</div>
		{/if}
	</div>
	{#key selected.length > 0}
		<div
			class="mb-4 flex w-full flex-row items-center justify-start gap-2"
			in:slide={{ axis: 'y' }}
			out:slide={{ axis: 'y' }}
		>
			{#if selected.length > 0}
				<p class="mr-2 font-semibold">{selected.length}/{data.memberships.total} Selected:</p>
			{/if}
			{#if selected.length > 0}
				{#if validatePermissions(data.membership, ['remove_members'])}
					<button
						class="bg-inset rounded px-1 py-1.5 font-semibold shadow-inner shadow-black/30 transition hover:cursor-pointer hover:bg-red-500/30"
						onclick={() => selected.forEach(async ({ user: { id } }) => kickMember(id))}
					>
						Kick
					</button>
				{/if}
				{#if validatePermissions(data.membership, ['manage_permissions'])}
					<Dropdown
						items={availablePermissions}
						onSelect={(perm) =>
							selected.forEach(async (membership) => addPermissionToMembership(membership, perm))}
						position="bottom-left"
						title="Add Permission to Selected"
						showArrow={false}
						show={false}
						hideCurrentSelection={true}
					>
						{#snippet icon()}
							<div
								class="bg-inset rounded px-1 py-1.5 font-semibold shadow-inner shadow-black/30 transition hover:cursor-pointer hover:bg-green-500/30"
							>
								Add Permission
							</div>
						{/snippet}
						{#snippet itemSnippet(perm)}
							{@render permissionItem(perm)}
						{/snippet}
					</Dropdown>

					<Dropdown
						items={availablePermissions}
						onSelect={(perm) =>
							selected.forEach(async (membership) =>
								removePermissionFromMembership(membership, perm)
							)}
						position="bottom-left"
						title="Remove Permission from Selected"
						showArrow={false}
						show={false}
						hideCurrentSelection={true}
					>
						{#snippet icon()}
							<div
								class="bg-inset rounded px-1 py-1.5 font-semibold shadow-inner shadow-black/30 transition hover:cursor-pointer hover:bg-orange-500/30"
							>
								Remove Permission
							</div>
						{/snippet}
						{#snippet itemSnippet(perm)}
							{@render permissionItem(perm)}
						{/snippet}
					</Dropdown>
				{/if}
			{/if}
		</div>
	{/key}

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
			},
			{
				label: $LL.memberships.actions(),
				width: '1fr',
				snippet: removeSnippet
			}
		]}
		data={memberships}
		loadMore={async (offset, limit) => {
			const result = await api.get<Paginated<MembershipRead>, 'group'>(
				`/memberships?offset=${offset}&limit=${limit}`,
				{
					sort: [{ field: 'accepted', direction: 'asc' }],
					filters: [
						{
							field: 'group_id',
							operator: '==',
							value: group?.id
						}
					]
				}
			);
			if (!result.success) {
				notification(result.error);
				return undefined;
			}
			return result.data;
		}}
		step={20}
		selectable
		onSelectionChange={handleSelectionChange}
		rowBgClass="bg-inset/90"
	/>
</div>

{#snippet permissionItem(perm: Permission)}
	<p class="text-text p-1 text-left">{$LL.permissions[perm]?.() || perm}</p>
{/snippet}

{#snippet usernameSnippet(membership: Omit<MembershipRead, 'group'>)}
	<div class="text-text flex flex-row items-center">
		<p class="font-medium">{membership.user.username || 'Unknown User'}</p>
		{#if membership.user.first_name || membership.user.last_name}
			<p class="text-text/70 ml-1">
				({membership.user.first_name || ''}
				{membership.user.last_name || ''})
			</p>
		{/if}
	</div>
{/snippet}

{#snippet badgeSnippet(membership: Omit<MembershipRead, 'group'>)}
	<span
		class="flex w-fit flex-row rounded-full px-2 py-1 text-xs font-semibold uppercase"
		class:bg-blue-100={membership.accepted && !membership.is_owner}
		class:text-blue-800={membership.accepted && !membership.is_owner}
		class:bg-yellow-100={!membership.accepted}
		class:text-yellow-800={!membership.accepted}
		class:bg-green-100={membership.is_owner}
		class:text-green-800={membership.is_owner}
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

{#snippet permissionsSnippet(membership: Omit<MembershipRead, 'group'>)}
	<div class="flex flex-wrap items-center gap-1.5">
		{#each membership.permissions as perm (perm)}
			<div
				class="bg-background text-text h-5.5 flex flex-row items-center rounded text-xs shadow-inner shadow-black/30"
				in:scale
				out:scale
			>
				<p class="whitespace-nowrap p-1.5">{$LL.permissions[perm]?.() || perm}</p>
				{#if validatePermissions(data.membership, ['manage_permissions'])}
					<button
						onclick={() => removePermissionFromMembership(membership, perm)}
						class="h-full w-full rounded-r bg-black/10 shadow-black/20 transition-all hover:cursor-pointer hover:bg-red-500/30 hover:shadow-inner"
						aria-label="Remove {perm} permission"
					>
						<RemoveIcon class="h-full w-full" />
					</button>
				{/if}
			</div>
		{/each}

		{#key membership.permissions}
			<div in:scale out:scale>
				<Dropdown
					items={availablePermissions.filter((p) => !membership.permissions.includes(p))}
					onSelect={(perm) => addPermissionToMembership(membership, perm)}
					position="bottom-left"
					title="Add Permission"
					showArrow={false}
					show={false}
					hideCurrentSelection={true}
					allowSelection={validatePermissions(data.membership, {
						or: ['manage_permissions', 'remove_members']
					})}
				>
					{#snippet icon()}
						{#if validatePermissions( data.membership, ['manage_permissions'] ) && availablePermissions.filter((p) => !membership.permissions.includes(p)).length > 0}
							<AddIcon
								class="w-5.5 bg-background text-text h-full rounded shadow-inner shadow-black/20 transition-all hover:bg-green-500/30"
							/>
						{/if}
					{/snippet}
					{#snippet itemSnippet(perm)}
						{@render permissionItem(perm)}
					{/snippet}
				</Dropdown>
			</div>
		{/key}
	</div>
{/snippet}

{#snippet removeSnippet(membership: Omit<MembershipRead, 'group'>)}
	{@const useRemoveButton = 
	validatePermissions(data.membership, ['remove_members']) && 
	!membership.is_owner && 
	!(membership.permissions.includes('administrator') || membership.permissions.includes('manage_permissions'))}

	{@const useLeaveButton =
		data.sessionUser.id === membership.user.id && !membership.is_owner}
	
	{#if useLeaveButton || useRemoveButton }
		<button
			onclick={async () => {
				if (confirm(useLeaveButton ? `Are you sure you want to leave the group?` : `Are you sure you want to kick ${membership.user.username} from the group?`)) {
					const success = useLeaveButton ? await leaveGroup() : await kickMember(membership.user.id);
					if (success) {
						data.memberships = {
							...data.memberships,
							data: data.memberships.data.filter((m) => m.user.id !== membership.user.id)
						};
						if (useLeaveButton) {
							notification('success', 'You have left the group.');
							invalidateAll();
						}
					}
				}
			}}
			class="text-text h-full w-fit rounded rounded-r bg-red-500/10 p-1 shadow-black/20 transition-all hover:cursor-pointer hover:bg-red-500/30 hover:shadow-inner"
			aria-label="Kick {membership.user.username} from the group"
		>
			{useLeaveButton ? $LL.memberships.leave() : $LL.memberships.kick()}
		</button>
	{/if}
{/snippet}
