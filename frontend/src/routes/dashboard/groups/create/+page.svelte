<script lang="ts">
	import type { GroupCreate, GroupRead, Permission } from '$api/types';
	import { permissionSchema } from '$api/schemas';
	import { goto } from '$app/navigation';
	import LL from '$i18n/i18n-svelte';
	import AddIcon from '~icons/material-symbols/add-circle-outline';
	import GroupIcon from '~icons/material-symbols/group-outline';
	import Loading from '~icons/svg-spinners/90-ring-with-bg';
	import { api } from '$api/client';
	import { notification } from '$lib/stores/notificationStore';

	let groupName: string = $state('');
	let selectedPermissions: Permission[] = $state([]);
	let isLoading: boolean = $state(false);
	let errorMessage: string = $state('');
	let successMessage: string = $state('');

	const allPermissions: Permission[] = permissionSchema.options.map((option) => option.value);

	const permissionGroups: Record<string, Permission[]> = {
		administration: ['administrator'],
		comments: [
			'add_comments',
			'remove_comments',
			'view_public_comments',
			'view_restricted_comments'
		],
		documents: ['upload_documents', 'view_restricted_documents', 'delete_documents'],
		members: ['add_members', 'remove_members', 'manage_permissions'],
		reactions: ['add_reactions', 'remove_reactions'],
		shareLinks: ['manage_share_links']
	};

	function togglePermission(permission: Permission): void {
		const index = selectedPermissions.indexOf(permission);
		if (index > -1) {
			selectedPermissions.splice(index, 1);
		} else {
			selectedPermissions.push(permission);
		}
	}

	function selectAll(): void {
		selectedPermissions = [...allPermissions];
	}

	function clearAll(): void {
		selectedPermissions = [];
	}

	function selectGroup(groupPermissions: Permission[]): void {
		for (const permission of groupPermissions) {
			if (!selectedPermissions.includes(permission)) {
				selectedPermissions.push(permission);
			}
		}
	}

	function clearGroup(groupPermissions: Permission[]): void {
		selectedPermissions = selectedPermissions.filter((p) => !groupPermissions.includes(p));
	}

	function isGroupFullySelected(groupPermissions: Permission[]): boolean {
		return groupPermissions.every((p) => selectedPermissions.includes(p));
	}

	function isGroupPartiallySelected(groupPermissions: Permission[]): boolean {
		return (
			groupPermissions.some((p) => selectedPermissions.includes(p)) &&
			!isGroupFullySelected(groupPermissions)
		);
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
			return;
		}

		isLoading = false;
		goto(`/dashboard/groups/${result.data.id}`);
	}
</script>

<div class="flex h-full w-full flex-col gap-4 p-6">
	<!-- Header Section -->
	<div class="flex flex-row items-center gap-3">
		<a href="/dashboard" class="text-text/70 hover:text-text transition-colors">Dashboard</a>
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

			<label for="groupName" class="text-text/70 text-sm font-semibold">Group Name *</label>
			<input
				id="groupName"
				type="text"
				bind:value={groupName}
				required
				placeholder="Enter group name"
				class="border-text/20 bg-text/5 focus:border-text/50 rounded-md border px-4 py-2 transition-colors focus:outline-none"
				disabled={isLoading}
			/>
		</div>

		<hr class="border-text/20" />

		<!-- Default Permissions -->
		<div class="flex flex-col gap-4">
			<div class="flex flex-row items-center justify-between">
				<h2 class="text-xl font-semibold">Default Member Permissions</h2>
				<div class="flex flex-row gap-2">
					<button
						type="button"
						onclick={selectAll}
						class="bg-text/10 hover:bg-text/20 rounded-md px-3 py-1 text-sm transition-all"
						disabled={isLoading}
					>
						Select All
					</button>
					<button
						type="button"
						onclick={clearAll}
						class="bg-text/10 hover:bg-text/20 rounded-md px-3 py-1 text-sm transition-all"
						disabled={isLoading}
					>
						Clear All
					</button>
				</div>
			</div>

			<p class="text-text/70 text-sm">
				Select the default permissions that new members will have when joining this group.
			</p>

			<!-- Permissions by Category -->
			<div class="flex flex-col gap-4">
				{#each Object.entries(permissionGroups) as [groupKey, groupPermissions] (groupKey)}
					<div class="flex flex-col gap-2">
						<div class="flex flex-row items-center justify-between">
							<h3 class="text-text/80 text-sm font-semibold">
								{$LL.permissionGroups[groupKey as keyof typeof $LL.permissionGroups]()}
							</h3>
							<div class="flex flex-row gap-2">
								{#if isGroupFullySelected(groupPermissions)}
									<button
										type="button"
										onclick={() => clearGroup(groupPermissions)}
										class="text-text/60 hover:text-text text-xs transition-colors"
										disabled={isLoading}
									>
										Clear
									</button>
								{:else}
									<button
										type="button"
										onclick={() => selectGroup(groupPermissions)}
										class="text-primary hover:text-primary/80 text-xs transition-colors"
										disabled={isLoading}
									>
										{isGroupPartiallySelected(groupPermissions) ? 'Select All' : 'Select'}
									</button>
								{/if}
							</div>
						</div>
						<div class="flex flex-col">
							{#each groupPermissions as permission (permission)}
								{@const isSelected = selectedPermissions.includes(permission)}
								<label
									class="bg-inset hover:bg-text/10 flex cursor-pointer flex-row items-center gap-2 p-2 transition-all"
									style={isSelected ? 'background-color: rgba(var(--primary-rgb), 0.1);' : ''}
								>
									<input
										type="checkbox"
										checked={isSelected}
										onchange={() => togglePermission(permission)}
										class="h-4 w-4 shrink-0"
										disabled={isLoading}
									/>
									<span class="text-sm">{$LL.permissions[permission]()}</span>
								</label>
							{/each}
						</div>
					</div>
				{/each}
			</div>
		</div>

		<hr class="border-text/20" />

		<!-- Submit Button -->
		<div class="flex flex-row justify-end gap-2">
			<a href="/dashboard" class="bg-text/10 hover:bg-text/20 rounded-md px-6 py-2 transition-all">
				Cancel
			</a>
			<button
				type="submit"
				disabled={isLoading || !groupName.trim()}
				class="bg-primary text-background hover:bg-primary/80 disabled:bg-text/30 flex flex-row items-center gap-2 rounded-md px-6 py-2 transition-all disabled:cursor-not-allowed"
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
