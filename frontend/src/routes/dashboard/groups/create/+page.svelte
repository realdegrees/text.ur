<script lang="ts">
	import type { GroupCreate, GroupRead, Permission } from '$api/types';
	import { permissionSchema } from '$api/schemas';
	import { goto } from '$app/navigation';
	import LL from '$i18n/i18n-svelte';
	import AddIcon from '~icons/material-symbols/add-2-rounded';
	import GroupIcon from '~icons/material-symbols/group-outline';
	import Loading from '~icons/svg-spinners/90-ring-with-bg';
	import { api } from '$api/client';
	import { notification } from '$lib/stores/notificationStore';
	import Dropdown from '$lib/components/dropdown.svelte';
	import Badge from '$lib/components/badge.svelte';
	import { scale } from 'svelte/transition';

	let groupName: string = $state('');
	let selectedPermissions: Permission[] = $state([]);
	let isLoading: boolean = $state(false);
	let errorMessage: string = $state('');
	let successMessage: string = $state('');

	const availablePermissions = permissionSchema.options.map((p) => p.value);

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

		isLoading = false;
		goto(`/dashboard/groups/${result.data.id}/documents`, { invalidateAll: true });
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

			<div
				class="flex flex-wrap items-center gap-1.5 rounded-md border border-text/20 bg-text/5 p-3"
			>
				{#each selectedPermissions as perm (perm)}
					<Badge
						item={perm}
						label={$LL.permissions[perm]?.() || perm}
						onRemove={removePermission}
						disabled={isLoading}
					/>
				{/each}

				{#key selectedPermissions.length}
					<div in:scale out:scale>
						<Dropdown
							items={availablePermissions.filter((p) => !selectedPermissions.includes(p))}
							onSelect={(perm) => addPermission(perm)}
							position="bottom-left"
							title="Add Permission"
							showArrow={false}
							show={false}
							hideCurrentSelection={true}
							allowSelection={true}
						>
							{#snippet icon()}
								{#if availablePermissions.filter((p) => !selectedPermissions.includes(p)).length > 0}
									<AddIcon
										class="h-full w-5.5 rounded bg-background text-text shadow-inner shadow-black/20 transition-all hover:bg-green-500/30"
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

{#snippet permissionItem(perm: Permission)}
	<p class="p-1 text-left text-text">{$LL.permissions[perm]?.() || perm}</p>
{/snippet}
