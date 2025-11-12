<script lang="ts">
	import type { GroupCreate, GroupRead, Permission } from '$api/types';
	import { permissionSchema } from '$api/schemas';
	import { goto } from '$app/navigation';
	import LL from '$i18n/i18n-svelte';
	import AddIcon from '~icons/material-symbols/add-circle-outline';
	import GroupIcon from '~icons/material-symbols/group-outline';
	import Loading from '~icons/svg-spinners/90-ring-with-bg';
	import { api } from '$api/client';

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
		errorMessage = '';
		successMessage = '';

		if (!groupName.trim()) {
			errorMessage = 'Group name is required';
			return;
		}

		isLoading = true;

		try {
			const group = await api.fetch<GroupRead>('/groups', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					name: groupName.trim(),
					default_permissions: selectedPermissions
				} satisfies GroupCreate)
			});

			successMessage = 'Group created successfully!';

			goto(`/dashboard/groups/${group.id}`);
		} catch (err) {
			errorMessage = err instanceof Error ? err.message : 'An error occurred';
		} finally {
			isLoading = false;
		}
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
			<div class="flex flex-row items-center justify-between">
				<h2 class="text-xl font-semibold">Default Member Permissions</h2>
				<div class="flex flex-row gap-2">
					<button
						type="button"
						onclick={selectAll}
						class="rounded-md bg-text/10 px-3 py-1 text-sm transition-all hover:bg-text/20"
						disabled={isLoading}
					>
						Select All
					</button>
					<button
						type="button"
						onclick={clearAll}
						class="rounded-md bg-text/10 px-3 py-1 text-sm transition-all hover:bg-text/20"
						disabled={isLoading}
					>
						Clear All
					</button>
				</div>
			</div>

			<p class="text-sm text-text/70">
				Select the default permissions that new members will have when joining this group.
			</p>

			<!-- Permissions by Category -->
			<div class="flex flex-col gap-4">
				{#each Object.entries(permissionGroups) as [groupKey, groupPermissions] (groupKey)}
					<div class="flex flex-col gap-2">
						<div class="flex flex-row items-center justify-between">
							<h3 class="text-sm font-semibold text-text/80">
								{$LL.permissionGroups[groupKey as keyof typeof $LL.permissionGroups]()}
							</h3>
							<div class="flex flex-row gap-2">
								{#if isGroupFullySelected(groupPermissions)}
									<button
										type="button"
										onclick={() => clearGroup(groupPermissions)}
										class="text-xs text-text/60 transition-colors hover:text-text"
										disabled={isLoading}
									>
										Clear
									</button>
								{:else}
									<button
										type="button"
										onclick={() => selectGroup(groupPermissions)}
										class="text-xs text-primary transition-colors hover:text-primary/80"
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
									class="flex cursor-pointer flex-row items-center gap-2 bg-inset p-2 transition-all hover:bg-text/10"
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
			<a href="/dashboard" class="rounded-md bg-text/10 px-6 py-2 transition-all hover:bg-text/20">
				Cancel
			</a>
			<button
				type="submit"
				disabled={isLoading || !groupName.trim()}
				class="flex flex-row items-center gap-2 rounded-md bg-primary px-6 py-2 text-background transition-all hover:bg-primary/80 disabled:cursor-not-allowed disabled:bg-text/30"
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
