<script lang="ts">
	import type { GroupCreate, GroupRead, Permission } from '$api/types';
	import AddIcon from '~icons/material-symbols/add-2-rounded';
	import GroupIcon from '~icons/material-symbols/group-outline';
	import Loading from '~icons/svg-spinners/90-ring-with-bg';
	import { api } from '$api/client';
	import { notification } from '$lib/stores/notificationStore';
	import PermissionSelector from '$lib/components/permissionSelector.svelte';

	let groupName: string = $state('');
	let selectedPermissions: Permission[] = $state([]);
	let isLoading: boolean = $state(false);
	let errorMessage: string = $state('');
	let successMessage: string = $state('');

	function addPermission(permission: Permission): void {
		if (!selectedPermissions.includes(permission)) {
			selectedPermissions = [...selectedPermissions, permission];
		}
	}

	function removePermission(permission: Permission): void {
		selectedPermissions = selectedPermissions.filter((p) => p !== permission);
	}

	async function handleSubmit(event: Event): Promise<void> {
		event.preventDefault();

		if (!groupName.trim()) {
			errorMessage = 'Group name is required';
			return;
		}

		isLoading = true;

		const result = await api.post<GroupRead>('/groups', {
			name: groupName.trim(),
			default_permissions: selectedPermissions
		} satisfies GroupCreate);

		if (!result.success) {
			notification(result.error);
			isLoading = false;
			return;
		}

		if (!result.data) {
			notification('error', 'Failed to create group: No data returned');
			isLoading = false;
			return;
		}

		isLoading = false;

		// Hard navigation to ensure fresh page load
		window.location.href = `/dashboard/groups/${result.data.id}/documents`;
	}
</script>

<div class="flex h-full w-full flex-col gap-4 p-6">
	<!-- Header Section -->
	<div class="flex flex-row items-center gap-3">
		<a href="/dashboard" class="text-text/70 transition-colors hover:text-text">Dashboard</a>
		<span class="text-text/50">/</span>
		<h1 class="text-2xl font-bold">Create New Group</h1>
	</div>

	<hr class="border-text/20" />

	<!-- Form Section -->
	<form onsubmit={handleSubmit} class="flex flex-col gap-6">
		<!-- Error Message -->
		{#if errorMessage}
			<div
				class="rounded-md border border-red-300 bg-red-100 p-3 text-red-700 dark:border-red-700 dark:bg-red-900/30 dark:text-red-300"
			>
				{errorMessage}
			</div>
		{/if}

		<!-- Success Message -->
		{#if successMessage}
			<div
				class="rounded-md border border-green-300 bg-green-100 p-3 text-green-700 dark:border-green-700 dark:bg-green-900/30 dark:text-green-300"
			>
				{successMessage}
			</div>
		{/if}

		<!-- Group Name -->
		<div class="flex flex-col gap-2">
			<div class="flex flex-row items-center gap-2">
				<GroupIcon class="h-6 w-6" />
				<h2 class="text-xl font-semibold">Group Details</h2>
			</div>

			<label for="groupName" class="text-sm font-semibold text-text/70">Group Name *</label>
			<input
				id="groupName"
				type="text"
				bind:value={groupName}
				required
				placeholder="Enter group name"
				class="rounded-md border border-text/20 bg-text/5 px-4 py-2 transition-colors focus:border-text/50 focus:outline-none"
				disabled={isLoading}
			/>
		</div>

		<hr class="border-text/20" />

		<!-- Default Permissions -->
		<div class="flex flex-col gap-4">
			<h2 class="text-xl font-semibold">Default Member Permissions</h2>

			<p class="text-sm text-text/70">
				Select the default permissions that new members will have when joining this group.
			</p>

			<PermissionSelector
				bind:selectedPermissions
				onAdd={addPermission}
				onRemove={removePermission}
				disabled={isLoading}
			/>
		</div>

		<hr class="border-text/20" />

		<!-- Submit Button -->
		<div class="flex flex-row justify-end gap-2">
			<a href="/dashboard" class="rounded-md bg-text/10 px-6 py-2 transition-all hover:bg-text/20">
				Cancel
			</a>
			<button
				type="submit"
				disabled={isLoading || !groupName.trim()}
				class="flex flex-row items-center gap-2 rounded-md bg-primary px-6 py-2 text-text transition-all hover:bg-primary/80 disabled:cursor-not-allowed disabled:bg-text/30"
			>
				{#if isLoading}
					<Loading class="h-5 w-5" />
					<span>Creating...</span>
				{:else}
					<AddIcon class="h-5 w-5" />
					<span>Create Group</span>
				{/if}
			</button>
		</div>
	</form>
</div>
