<script lang="ts">
	import AddIcon from '~icons/material-symbols/add-2-rounded';
	import DeleteIcon from '~icons/material-symbols/delete-outline';
	import EditIcon from '~icons/material-symbols/edit-outline';
	import SaveIcon from '~icons/material-symbols/save-outline';
	import CancelIcon from '~icons/material-symbols/close-rounded';
	import CopyIcon from '~icons/material-symbols/content-copy-outline';
	import { api } from '$api/client';
	import { notification } from '$lib/stores/notificationStore';
	import { invalidateAll } from '$app/navigation';
	import type { ShareLinkCreate, ShareLinkRead, ShareLinkUpdate, Permission } from '$api/types';
	import type { Paginated } from '$api/pagination';
	import Badge from '$lib/components/badge.svelte';
	import PermissionSelector from '$lib/components/permissionSelector.svelte';
	import LL from '$i18n/i18n-svelte.js';

	let { shareLinks, groupId }: {
		shareLinks: Paginated<ShareLinkRead>;
		groupId: string;
	} = $props();

	let showCreateForm = $state(false);
	let editingLinkId: number | null = $state(null);

	// Create form state
	let createFormPermissions: Permission[] = $state([]);
	let createFormLabel = $state('');
	let createFormExpiresAt = $state<string | null>(null);
	let createFormAllowAnonymous = $state(false);

	// Edit form state
	let editFormPermissions: Permission[] = $state([]);
	let editFormLabel = $state('');
	let editFormExpiresAt = $state<string | null>(null);
	let editFormAllowAnonymous = $state(false);
	let editFormRotateToken = $state(false);

	function resetCreateForm() {
		createFormPermissions = [];
		createFormLabel = '';
		createFormExpiresAt = null;
		createFormAllowAnonymous = false;
		showCreateForm = false;
	}

	function startEdit(link: ShareLinkRead) {
		editingLinkId = link.id;
		editFormPermissions = [...link.permissions];
		editFormLabel = link.label || '';
		editFormExpiresAt = link.expires_at || null;
		editFormAllowAnonymous = link.allow_anonymous_access;
		editFormRotateToken = false;
	}

	function cancelEdit() {
		editingLinkId = null;
		editFormPermissions = [];
		editFormLabel = '';
		editFormExpiresAt = null;
		editFormAllowAnonymous = false;
		editFormRotateToken = false;
	}

	async function handleCreate() {
		const createData: ShareLinkCreate = {
			permissions: createFormPermissions,
			label: createFormLabel || null,
			expires_at: createFormExpiresAt || null,
			allow_anonymous_access: createFormAllowAnonymous,
		};

		const result = await api.post(`/groups/${groupId}/sharelinks`, createData);

		if (result.success) {
			notification('success', 'Share link created successfully');
			resetCreateForm();
			await invalidateAll();
		} else {
			notification(result.error);
		}
	}

	async function handleUpdate(linkId: number) {
		const updateData: ShareLinkUpdate = {
			permissions: editFormPermissions.length > 0 ? editFormPermissions : null,
			label: editFormLabel || null,
			expires_at: editFormExpiresAt,
			allow_anonymous_access: editFormAllowAnonymous,
			rotate_token: editFormRotateToken || null
		};

		const result = await api.update(`/groups/${groupId}/sharelinks/${linkId}`, updateData);

		if (result.success) {
			notification('success', 'Share link updated successfully');
			cancelEdit();
			await invalidateAll();
		} else {
			notification(result.error);
		}
	}

	async function handleDelete(linkId: number) {
		const confirmed = confirm('Are you sure you want to delete this share link?');
		if (!confirmed) return;

		const result = await api.delete(`/groups/${groupId}/sharelinks/${linkId}`);

		if (result.success) {
			notification('success', 'Share link deleted successfully');
			await invalidateAll();
		} else {
			notification(result.error);
		}
	}

	async function copyLinkToClipboard(token: string) {
		const link = `${window.location.origin}/sharelink/${token}`;
		try {
			await navigator.clipboard.writeText(link);
			notification('success', 'Link copied to clipboard');
		} catch {
			notification('error', 'Failed to copy link');
		}
	}

	function addPermission(permission: Permission, isCreate: boolean) {
		if (isCreate) {
			if (!createFormPermissions.includes(permission)) {
				createFormPermissions = [...createFormPermissions, permission];
			}
		} else {
			if (!editFormPermissions.includes(permission)) {
				editFormPermissions = [...editFormPermissions, permission];
			}
		}
	}

	function removePermission(permission: Permission, isCreate: boolean) {
		if (isCreate) {
			createFormPermissions = createFormPermissions.filter((p) => p !== permission);
		} else {
			editFormPermissions = editFormPermissions.filter((p) => p !== permission);
		}
	}

	function formatDate(date: string | null | undefined): string {
		if (!date) return 'Never';
		return new Date(date).toLocaleString();
	}
</script>

<div class="flex flex-col gap-4">
	<!-- Header -->
	<div class="flex items-center justify-between">
		<div>
			<h2 class="text-lg font-semibold">Share Links</h2>
			<p class="text-sm text-text/70">Create shareable links with specific permissions</p>
		</div>
		{#if !showCreateForm}
			<button
				type="button"
				onclick={() => (showCreateForm = true)}
				class="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-background transition-all hover:bg-primary/80"
			>
				<AddIcon class="h-5 w-5" />
				<span>Create Link</span>
			</button>
		{/if}
	</div>

	<!-- Create Form -->
	{#if showCreateForm}
		<div class="flex flex-col gap-3 rounded border border-text/20 bg-background/50 p-4">
			<div class="flex items-center justify-between">
				<h3 class="font-semibold">New Share Link</h3>
				<button
					type="button"
					onclick={resetCreateForm}
					class="text-text/50 transition hover:text-text"
				>
					<CancelIcon class="h-5 w-5" />
				</button>
			</div>

			<input
				type="text"
				bind:value={createFormLabel}
				maxlength="30"
				placeholder="Label (optional)"
				class="rounded border border-text/20 bg-background px-3 py-2 text-sm transition-colors focus:border-text/50 focus:outline-none"
			/>

			<div class="flex flex-col gap-1">
				<div class="text-xs font-semibold text-text/70">Permissions *</div>
				<PermissionSelector
					bind:selectedPermissions={createFormPermissions}
					onAdd={(p: Permission) => addPermission(p, true)}
					onRemove={(p: Permission) => removePermission(p, true)}
					compact
				/>
			</div>

			<div class="flex flex-col gap-2">
				<div class="flex items-center justify-between gap-2">
					<label for="create-expires" class="text-xs font-semibold text-text/70"
						>Expires: {formatDate(createFormExpiresAt)}</label
					>
					{#if createFormExpiresAt}
						<button
							type="button"
							onclick={() => (createFormExpiresAt = null)}
							class="text-text/50 transition hover:text-text"
							title="Clear expiration"
						>
							<CancelIcon class="h-4 w-4" />
						</button>
					{/if}
				</div>
				<input
					id="create-expires"
					type="datetime-local"
					bind:value={createFormExpiresAt}
					class="rounded border border-text/20 bg-background px-3 py-2 text-sm transition-colors focus:border-text/50 focus:outline-none"
				/>
			</div>

			<label class="flex items-center gap-2 text-sm">
				<input type="checkbox" bind:checked={createFormAllowAnonymous} class="h-4 w-4 rounded" />
				<span class="text-text/70">Allow anonymous access</span>
			</label>

			<button
				type="button"
				onclick={handleCreate}
				class="flex items-center justify-center gap-2 rounded bg-primary px-4 py-2 text-background transition hover:bg-primary/80"
			>
				<SaveIcon class="h-5 w-5" />
				<span>Create</span>
			</button>
		</div>
	{/if}

	<!-- Links List -->
	{#if shareLinks.data.length === 0}
		<p class="text-center text-sm text-text/50">No share links yet. Create one to get started.</p>
	{:else}
		{#each shareLinks.data as link (link.id)}
			<div class="flex flex-col gap-2 rounded border border-text/20 bg-background/50 p-3">
				{#if editingLinkId === link.id}
					<!-- Edit Mode -->
					<div class="flex items-center justify-between">
						<h3 class="font-semibold">Edit Link</h3>
						<button
							type="button"
							onclick={cancelEdit}
							class="text-text/50 transition hover:text-text"
						>
							<CancelIcon class="h-5 w-5" />
						</button>
					</div>

					<input
						type="text"
						bind:value={editFormLabel}
						maxlength="30"
						placeholder="Label (optional)"
						class="rounded border border-text/20 bg-background px-3 py-2 text-sm transition-colors focus:border-text/50 focus:outline-none"
					/>

					<div class="flex flex-col gap-1">
						<div class="text-xs font-semibold text-text/70">Permissions</div>
						<PermissionSelector
							bind:selectedPermissions={editFormPermissions}
							onAdd={(p: Permission) => addPermission(p, false)}
							onRemove={(p: Permission) => removePermission(p, false)}
							compact
						/>
					</div>

					<div class="flex flex-col gap-2">
						<div class="flex items-center justify-between gap-2">
							<label for="edit-expires-{link.id}" class="text-xs font-semibold text-text/70"
								>Expires: {formatDate(editFormExpiresAt)}</label
							>
							{#if editFormExpiresAt}
								<button
									type="button"
									onclick={() => (editFormExpiresAt = null)}
									class="text-text/50 transition hover:text-text"
									title="Clear expiration"
								>
									<CancelIcon class="h-4 w-4" />
								</button>
							{/if}
						</div>
						<input
							id="edit-expires-{link.id}"
							type="datetime-local"
							bind:value={editFormExpiresAt}
							class="rounded border border-text/20 bg-background px-3 py-2 text-sm transition-colors focus:border-text/50 focus:outline-none"
						/>
					</div>

					<label class="flex items-center gap-2 text-sm">
						<input type="checkbox" bind:checked={editFormAllowAnonymous} class="h-4 w-4 rounded" />
						<span class="text-text/70">Allow anonymous access</span>
					</label>

					<label class="flex items-center gap-2 text-sm">
						<input type="checkbox" bind:checked={editFormRotateToken} class="h-4 w-4 rounded" />
						<span class="text-text/70">Rotate token (invalidates old link)</span>
					</label>

					<button
						type="button"
						onclick={() => handleUpdate(link.id)}
						class="flex items-center justify-center gap-2 rounded bg-primary px-4 py-2 text-background transition hover:bg-primary/80"
					>
						<SaveIcon class="h-5 w-5" />
						<span>Save</span>
					</button>
				{:else}
					<!-- Display Mode -->
					<div class="flex items-start justify-between gap-2">
						<div class="flex flex-col gap-1">
							<div class="flex items-center gap-2">
								{#if link.label}
									<span class="font-semibold">{link.label}</span>
								{:else}
									<span class="font-semibold text-text/50">Untitled Link</span>
								{/if}
								{#if link.allow_anonymous_access}
									<span
										class="rounded bg-green-500/20 px-2 py-0.5 text-xs font-semibold text-green-600"
										>Anonymous</span
									>
								{/if}
							</div>
							<p class="text-xs text-text/50">
								by {link.author?.username || "Deleted User"} • Expires: {formatDate(link.expires_at)}
							</p>
						</div>
						<div class="flex gap-1">
							<button
								type="button"
								onclick={() => copyLinkToClipboard(link.token)}
								class="rounded bg-blue-500/20 p-2 transition hover:bg-blue-500/30"
								title="Copy Link"
							>
								<CopyIcon class="h-4 w-4" />
							</button>
							<button
								type="button"
								onclick={() => startEdit(link)}
								class="rounded bg-text/10 p-2 transition hover:bg-text/20"
								title="Edit"
							>
								<EditIcon class="h-4 w-4" />
							</button>
							<button
								type="button"
								onclick={() => handleDelete(link.id)}
								class="rounded bg-red-500/20 p-2 transition hover:bg-red-500/30"
								title="Delete"
							>
								<DeleteIcon class="h-4 w-4" />
							</button>
						</div>
					</div>

					<div class="flex flex-wrap gap-1">
						{#each link.permissions as perm (perm)}
							<Badge item={perm} label={$LL.permissions[perm as Permission]?.() || perm} />
						{/each}
					</div>
				{/if}
			</div>
		{/each}
	{/if}
</div>
