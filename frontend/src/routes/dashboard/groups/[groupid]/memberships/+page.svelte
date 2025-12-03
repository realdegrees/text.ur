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
	import TimeIcon from '~icons/ic/baseline-access-time';
	import { permissionSchema } from '$api/schemas';
	import LL from '$i18n/i18n-svelte.js';
	import { api } from '$api/client.js';
	import type { Paginated } from '$api/pagination.js';
	import { sessionStore } from '$lib/runes/session.svelte.js';
	import { notification } from '$lib/stores/notificationStore.js';
	import Dropdown from '$lib/components/dropdown.svelte';
	import PermissionSelector from '$lib/components/permissionSelector.svelte';
	import { slide } from 'svelte/transition';
	import AdvancedInput from '$lib/components/advancedInput.svelte';
	import { invalidateAll } from '$app/navigation';
	import ConfirmButton from '$lib/components/ConfirmButton.svelte';
	import PromoteIcon from '~icons/mdi/chevron-double-up';
	import KickIcon from '~icons/ic/sharp-person-remove';
	import LeaveIcon from '~icons/mdi/exit-run';
	import { formatDateTime } from '$lib/util/dateFormat';
	import ExpandablePermissionBadge from '$lib/components/expandablePermissionBadge.svelte';
	import { SvelteSet } from 'svelte/reactivity';

	let { data } = $props();
	let memberships = $derived(data.memberships);
	let group = $derived(data.membership.group);

	let selected = $state<Omit<MembershipRead, 'group'>[]>([]);
	let username = $state('');
	let selectedUser = $state<UserRead | undefined>(undefined);

	const availablePermissions = permissionSchema.options.map((p) => p.value);

	// Calculate permissions that should be excluded from bulk actions
	const bulkExcludedPermissions = $derived(() => {
		const excluded = new SvelteSet<Permission>(group.default_permissions);
		// Add sharelink permissions from all selected memberships
		selected.forEach((m) => {
			if (m.share_link) {
				m.share_link.permissions.forEach((p) => excluded.add(p));
			}
		});
		return Array.from(excluded);
	});

	const availableForBulkAdd = $derived(
		availablePermissions.filter((p) => !bulkExcludedPermissions().includes(p))
	);

	function handleSelectionChange(memberships: Omit<MembershipRead, 'group'>[]) {
		selected = memberships;
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
						invalidateAll();
					} else {
						notification(result.error);
					}
				});
		}
	}
</script>

<div class="p-4">
	<div class="mb-4 flex w-full flex-row items-center justify-between gap-2">
		{#if sessionStore.validatePermissions(['add_members'])}
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
				{#if sessionStore.validatePermissions(['remove_members'])}
					<button
						class="rounded bg-inset px-1 py-1.5 font-semibold shadow-inner shadow-black/30 transition hover:cursor-pointer hover:bg-red-500/30"
						onclick={async () => {
							await Promise.all(selected.map(({ user: { id } }) => kickMember(id)));
							await invalidateAll();
						}}
					>
						Kick
					</button>
				{/if}
				{#if sessionStore.validatePermissions(['manage_permissions'])}
					<Dropdown
						items={availableForBulkAdd}
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
								class="rounded bg-inset px-1 py-1.5 font-semibold shadow-inner shadow-black/30 transition hover:cursor-pointer hover:bg-green-500/30"
							>
								Add Permission
							</div>
						{/snippet}
						{#snippet itemSnippet(perm)}
							{@render permissionItem(perm)}
						{/snippet}
					</Dropdown>

					<Dropdown
						items={availableForBulkAdd}
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
								class="rounded bg-inset px-1 py-1.5 font-semibold shadow-inner shadow-black/30 transition hover:cursor-pointer hover:bg-orange-500/30"
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
					width: '2fr',
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
					width: '2fr',
					snippet: actionsSnippet
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
	<p class="p-1 text-left text-text">
		{($LL.permissions as Record<string, () => string>)[perm]?.() || perm}
	</p>
{/snippet}

{#snippet usernameSnippet(membership: Omit<MembershipRead, 'group'>)}
	<div class="flex flex-row items-center text-text">
		<p class="font-medium">{membership.user.username || 'Unknown User'}</p>
		{#if membership.user.first_name || membership.user.last_name}
			<p class="ml-1 whitespace-nowrap text-text/70">
				({membership.user.first_name || ''}
				{membership.user.last_name || ''})
			</p>
		{/if}
	</div>
{/snippet}

{#snippet badgeSnippet(membership: Omit<MembershipRead, 'group'>)}
	<div class="flex flex-wrap gap-1">
		{#if membership.share_link}
			<span
				class="flex w-fit flex-row rounded-full bg-purple-100 px-2 py-1 text-xs font-semibold text-purple-800 uppercase"
				title={membership.share_link.expires_at
					? `Expires at ${formatDateTime(membership.share_link.expires_at)}`
					: ''}
			>
				<TimeIcon class="mr-1 inline h-4 w-4 align-text-bottom" />
				Guest
			</span>
		{:else}
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
		{/if}
	</div>
{/snippet}

{#snippet permissionsSnippet(membership: Omit<MembershipRead, 'group'>)}
	{@const defaultPermissions = group.default_permissions}
	{@const sharelinkPermissions = membership.share_link?.permissions || []}
	{@const groupedPermissions = [...defaultPermissions, ...sharelinkPermissions]}
	{@const customPermissions = membership.permissions.filter((p) => !groupedPermissions.includes(p))}

		<PermissionSelector
			selectedPermissions={customPermissions}
			excludedPermissions={groupedPermissions}
			onAdd={(perm) => addPermissionToMembership(membership, perm)}
			onRemove={(perm) => removePermissionFromMembership(membership, perm)}
			showRemove={sessionStore.validatePermissions(['manage_permissions'])}
			allowSelection={sessionStore.validatePermissions({
				or: ['manage_permissions', 'remove_members']
			})}
		>
			{#snippet prepend()}
				<!-- Default Permissions Badge -->
				{#if defaultPermissions.length > 0}
					<ExpandablePermissionBadge
						permissions={defaultPermissions}
						label="Default"
						variant="default"
					/>
				{/if}

				<!-- Sharelink Permissions Badge -->
				{#if sharelinkPermissions.length > 0}
					<ExpandablePermissionBadge
						permissions={sharelinkPermissions}
						label="Sharelink"
						variant="sharelink"
					/>
				{/if}
			{/snippet}
		</PermissionSelector>
{/snippet}

{#snippet actionsSnippet(membership: Omit<MembershipRead, 'group'>)}
	{@const showRemoveButton =
		sessionStore.validatePermissions(['remove_members']) &&
		!membership.is_owner &&
		!membership.permissions.includes('administrator')}

	{@const showLeaveButton = data.sessionUser.id === membership.user.id && !membership.is_owner}
	{@const showPromoteButton = sessionStore.validatePermissions(['add_members'])}

	<div class="flex flex-row items-center justify-end gap-2">
		{#if membership.share_link && showPromoteButton}
			<ConfirmButton
				onConfirm={async () => {
					const result = await api.post(
						`/groups/${group.id}/memberships/promote/${membership.user.id}`,
						{}
					);

					if (result.success) {
						notification('success', 'Member promoted successfully.');
						invalidateAll();
					} else {
						notification(result.error);
					}
				}}
				slideoutDirection="left"
			>
				{#snippet button()}
					<div
						class="h-full w-fit rounded bg-green-400/50 p-1 text-text shadow-black/20 transition hover:cursor-pointer hover:bg-green-500/90 hover:shadow-inner"
						aria-label="Promote guest {membership.user.username} to a permanent member"
					>
						<PromoteIcon class="h-5 w-5" />
					</div>
				{/snippet}

				{#snippet slideout()}
					<p
						class="flex items-center bg-green-500/10 px-2 py-0.5 text-xs whitespace-nowrap text-green-500"
					>
						Promote to a permanent member?
					</p>
				{/snippet}
			</ConfirmButton>
		{/if}

		{#if showLeaveButton || showRemoveButton}
			<ConfirmButton
				onConfirm={async () => {
					const success = showLeaveButton
						? await leaveGroup()
						: await kickMember(membership.user.id);
					if (success) {
						notification(
							'success',
							showLeaveButton
								? 'You have left the group.'
								: `Removed ${membership.user.username} from the group.`
						);
						invalidateAll();
					}
				}}
				slideoutDirection="left"
			>
				{#snippet button()}
					<div
						class="h-full w-fit rounded bg-red-400/60 p-1 text-text shadow-black/20 transition hover:cursor-pointer hover:bg-red-500/70 hover:shadow-inner"
						aria-label={showLeaveButton
							? `Leave the group`
							: `Kick {membership.user.username} from the group`}
					>
						{#if showLeaveButton}
							<LeaveIcon class="h-5 w-5" />
						{:else}
							<KickIcon class="h-5 w-5" />
						{/if}
					</div>
				{/snippet}

				{#snippet slideout()}
					<p
						class="flex items-center bg-red-500/10 px-2 py-0.5 text-xs whitespace-nowrap text-red-500"
					>
						{showLeaveButton
							? 'Leave the group?'
							: `Remove ${membership.user.username} from the group?`}
					</p>
				{/snippet}
			</ConfirmButton>
		{/if}
	</div>
{/snippet}
