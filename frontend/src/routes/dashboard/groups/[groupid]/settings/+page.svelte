<script lang="ts">
	import SaveIcon from '~icons/material-symbols/save-outline';
	import DeleteIcon from '~icons/material-symbols/delete-outline';
	import TransferIcon from '~icons/material-symbols/swap-horiz';
	import AddIcon from '~icons/material-symbols/add-2-rounded';
	import { permissionSchema } from '$api/schemas';
	import { api } from '$api/client';
	import { notification } from '$lib/stores/notificationStore';
	import { sessionStore } from '$lib/runes/session.svelte.js';
	import { invalidateAll } from '$app/navigation';
	import type {
		GroupUpdate,
		GroupTransfer,
		Permission,
		UserRead,
		MembershipRead
	} from '$api/types';
	import type { Paginated } from '$api/pagination';
	import AdvancedInput from '$lib/components/advancedInput.svelte';
	import PermissionSelector from '$lib/components/permissionSelector.svelte';
	import LL from '$i18n/i18n-svelte.js';

	let { data } = $props();
	let group = $derived(data.membership.group);
	let isOwner = $derived(sessionStore.routeMembership?.is_owner);
	let defaultPermissions: Permission[] = $derived(group.default_permissions || []);

	let transferUsername: string = $state('');
	let selectedTransferUser: UserRead | undefined = $state(undefined);
	let showDeleteConfirm: boolean = $state(false);
	let showTransferConfirm: boolean = $state(false);
	let deleteConfirmText: string = $state('');
	let editableGroupName: string = $derived(group.name);

	async function handleSave(): Promise<void> {
		const updateData: GroupUpdate = {
			name: editableGroupName !== group.name ? editableGroupName : undefined,
			default_permissions: isOwner && defaultPermissions.length > 0 ? defaultPermissions : undefined
		};

		if (!updateData.name && !updateData.default_permissions) {
			notification('info', 'No changes to save');
			return;
		}

		const result = await api.update(`/groups/${group.id}`, updateData);

		if (result.success) {
			notification('success', 'Group settings updated successfully');
			await invalidateAll();
		} else {
			notification(result.error);
		}
	}

	async function handleDelete(): Promise<void> {
		if (deleteConfirmText !== group.name) {
			notification('error', 'Group name does not match');
			return;
		}

		const result = await api.delete(`/groups/${group.id}`);

		if (result.success) {
			notification('success', 'Group deleted successfully');
			// Hard navigation to ensure fresh page load
			window.location.href = '/dashboard';
		} else {
			notification(result.error);
		}
	}

	async function handleTransfer(): Promise<void> {
		if (!selectedTransferUser) {
			notification('error', 'Please select a user to transfer ownership to');
			return;
		}

		const transferData: GroupTransfer = {
			user_id: selectedTransferUser.id
		};

		const result = await api.post(`/groups/${group.id}/transfer`, transferData);

		if (result.success) {
			notification('success', 'Group ownership transferred successfully');
			showTransferConfirm = false;
			transferUsername = '';
			selectedTransferUser = undefined;
			await invalidateAll();
		} else {
			notification(result.error);
		}
	}

	async function fetchMemberOptions(search: string): Promise<UserRead[]> {
		const response = await api.get<Paginated<MembershipRead>, 'group'>(`/memberships`, {
			filters: [
				{ field: 'group_id', operator: '==', value: group.id },
				{ field: 'accepted', operator: '==', value: 'true' },
				{ field: 'user_id', operator: '!=', value: data.sessionUser.id.toString() }
			]
		});

		if (response.success) {
			const users = response.data.data.map((m) => m.user);
			return users.filter(
				(u) =>
					u.username.toLowerCase().includes(search.toLowerCase()) ||
					u.first_name?.toLowerCase().includes(search.toLowerCase()) ||
					u.last_name?.toLowerCase().includes(search.toLowerCase())
			);
		}
		return [];
	}

	function addDefaultPermission(permission: Permission): void {
		if (!defaultPermissions.includes(permission)) {
			defaultPermissions = [...defaultPermissions, permission];
		}
	}

	function removeDefaultPermission(permission: Permission): void {
		defaultPermissions = defaultPermissions.filter((p) => p !== permission);
	}
</script>

<div class="flex h-full w-full flex-col gap-6 p-6">
	<h1 class="text-2xl font-bold">Group Settings</h1>

	<!-- Settings Form -->
	<div class="flex flex-col gap-6">
		<!-- Group Name -->
		<div class="flex flex-col gap-2">
			<label for="groupName" class="text-sm font-semibold text-text/70">Group Name</label>
			<input
				id="groupName"
				type="text"
				bind:value={editableGroupName}
				class="rounded-md border border-text/20 bg-text/5 px-4 py-2 transition-colors focus:border-text/50 focus:outline-none"
			/>
		</div>

		<!-- Group ID (Read-only) -->
		<div class="flex flex-col gap-2">
			<label for="groupId" class="text-sm font-semibold text-text/70">Group ID</label>
			<input
				id="groupId"
				type="text"
				value={group?.id}
				readonly
				class="cursor-not-allowed rounded-md border border-text/20 bg-text/10 px-4 py-2 font-mono text-sm text-text/70"
			/>
		</div>

		<!-- Default Permissions (Owner only) -->
		{#if isOwner}
			<div class="flex flex-col gap-2">
				<div class="text-sm font-semibold text-text/70">Default Permissions</div>
				<p class="text-xs text-text/50">
					These permissions are automatically granted to new members when they join the group.
				</p>
				<PermissionSelector
					bind:selectedPermissions={defaultPermissions}
					onAdd={addDefaultPermission}
					onRemove={removeDefaultPermission}
				/>
			</div>
		{/if}

		<!-- Save Button -->
		<div class="flex flex-row justify-end gap-2">
			<button
				type="button"
				onclick={handleSave}
				class="flex flex-row items-center gap-2 rounded-md bg-primary px-6 py-2 text-background transition-all hover:bg-primary/80"
			>
				<SaveIcon class="h-5 w-5" />
				<span>Save Changes</span>
			</button>
		</div>

		<!-- Transfer Ownership (Owner only) -->
		{#if isOwner}
			<div
				class="mt-8 flex flex-col gap-4 rounded-md border border-orange-500/30 bg-orange-500/5 p-4"
			>
				<h2 class="text-lg font-semibold text-orange-500">Transfer Ownership</h2>
				<p class="text-sm text-text/70">
					Transfer ownership of this group to another member. You will lose owner privileges.
				</p>

				{#if !showTransferConfirm}
					<div class="flex flex-row items-end gap-2">
						<div class="w-64">
							<AdvancedInput
								fetchOptions={fetchMemberOptions}
								bind:value={transferUsername}
								bind:selected={selectedTransferUser}
								config={{ placeholder: 'Search member...' }}
								stringify={{
									option: (user) => `${user.username}`,
									hint: (s) => ` (${s?.first_name || ''} ${s?.last_name || ''})`
								}}
								onSubmit={() => {
									if (selectedTransferUser) {
										showTransferConfirm = true;
									}
								}}
							/>
						</div>
						<button
							type="button"
							class="rounded bg-orange-500/30 px-3 py-2.5 font-semibold shadow-inner shadow-black/30 transition hover:cursor-pointer hover:bg-orange-500/40"
							onclick={() => {
								if (selectedTransferUser) {
									showTransferConfirm = true;
								}
							}}
							disabled={!selectedTransferUser}
							class:opacity-50={!selectedTransferUser}
							class:cursor-not-allowed={!selectedTransferUser}
						>
							<TransferIcon class="inline h-5 w-5" />
							Transfer
						</button>
					</div>
				{:else}
					<div class="flex flex-col gap-3 rounded-md bg-orange-500/10 p-4">
						<p class="font-semibold text-orange-500">Confirm Transfer</p>
						<p class="text-sm text-text/70">
							Are you sure you want to transfer ownership to
							<span class="font-semibold"
								>{selectedTransferUser?.username}
								{#if selectedTransferUser?.first_name || selectedTransferUser?.last_name}
									({selectedTransferUser.first_name || ''}
									{selectedTransferUser.last_name || ''})
								{/if}</span
							>? This action cannot be undone.
						</p>
						<div class="flex flex-row gap-2">
							<button
								type="button"
								onclick={handleTransfer}
								class="rounded bg-orange-500/30 px-4 py-2 font-semibold transition hover:bg-orange-500/40"
							>
								Confirm Transfer
							</button>
							<button
								type="button"
								onclick={() => {
									showTransferConfirm = false;
									transferUsername = '';
									selectedTransferUser = undefined;
								}}
								class="rounded bg-text/10 px-4 py-2 font-semibold transition hover:bg-text/20"
							>
								Cancel
							</button>
						</div>
					</div>
				{/if}
			</div>
		{/if}

		<!-- Danger Zone (Owner only) -->
		{#if isOwner}
			<div class="mt-8 flex flex-col gap-4 rounded-md border border-red-500/30 bg-red-500/5 p-4">
				<h2 class="text-lg font-semibold text-red-500">Danger Zone</h2>
				<p class="text-sm text-text/70">
					Once you delete a group, there is no going back. Please be certain.
				</p>

				{#if !showDeleteConfirm}
					<button
						type="button"
						onclick={() => (showDeleteConfirm = true)}
						class="flex w-fit flex-row items-center gap-2 rounded-md bg-red-500/20 px-4 py-2 transition-all hover:bg-red-500/30"
					>
						<DeleteIcon class="h-5 w-5" />
						<span>Delete Group</span>
					</button>
				{:else}
					<div class="flex flex-col gap-3 rounded-md bg-red-500/10 p-4">
						<p class="font-semibold text-red-500">Confirm Deletion</p>
						<p class="text-sm text-text/70">
							Type the group name <span class="font-mono font-semibold">{group.name}</span> to confirm
							deletion:
						</p>
						<input
							type="text"
							bind:value={deleteConfirmText}
							placeholder={group.name}
							class="rounded-md border border-red-500/30 bg-text/5 px-4 py-2 transition-colors focus:border-red-500/50 focus:outline-none"
						/>
						<div class="flex flex-row gap-2">
							<button
								type="button"
								onclick={handleDelete}
								disabled={deleteConfirmText !== group.name}
								class="rounded bg-red-500/30 px-4 py-2 font-semibold transition hover:bg-red-500/40 disabled:cursor-not-allowed disabled:opacity-50"
							>
								Delete Group
							</button>
							<button
								type="button"
								onclick={() => {
									showDeleteConfirm = false;
									deleteConfirmText = '';
								}}
								class="rounded bg-text/10 px-4 py-2 font-semibold transition hover:bg-text/20"
							>
								Cancel
							</button>
						</div>
					</div>
				{/if}
			</div>
		{/if}
	</div>
</div>
