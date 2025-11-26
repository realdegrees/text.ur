<script lang="ts">
	import AddIcon from '~icons/material-symbols/add-2-rounded';
	import { api } from '$api/client';
	import { notification } from '$lib/stores/notificationStore';
	import { invalidateAll } from '$app/navigation';
	import type {
		ShareLinkCreate as ShareLinkCreateData,
		ShareLinkRead,
		ShareLinkUpdate,
		Permission
	} from '$api/types';
	import type { Paginated } from '$api/pagination';
	import ShareLinkDisplay from './ShareLinkDisplay.svelte';
	import ShareLinkEdit from './ShareLinkEdit.svelte';
	import ShareLinkCreate from './ShareLinkCreate.svelte';

	let {
		shareLinks,
		groupId
	}: {
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
	}

	function cancelEdit() {
		editingLinkId = null;
		editFormPermissions = [];
		editFormLabel = '';
		editFormExpiresAt = null;
		editFormAllowAnonymous = false;
	}

	async function handleCreate() {
		const createData: ShareLinkCreateData = {
			permissions: createFormPermissions,
			label: createFormLabel || null,
			expires_at: createFormExpiresAt || null,
			allow_anonymous_access: createFormAllowAnonymous
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
			permissions: editFormPermissions,
			label: editFormLabel || null,
			expires_at: editFormExpiresAt,
			allow_anonymous_access: editFormAllowAnonymous,
			rotate_token: null
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

	async function handleRotateToken(linkId: number) {
		const updateData: ShareLinkUpdate = {
			rotate_token: true
		};

		const result = await api.update(`/groups/${groupId}/sharelinks/${linkId}`, updateData);

		if (result.success) {
			notification('success', 'Token rotated successfully. The old link is now invalid.');
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
		<ShareLinkCreate
			bind:permissions={createFormPermissions}
			bind:label={createFormLabel}
			bind:expiresAt={createFormExpiresAt}
			bind:allowAnonymous={createFormAllowAnonymous}
			onCreate={handleCreate}
			onCancel={resetCreateForm}
		/>
	{/if}

	<!-- Links List -->
	{#if shareLinks.data.length === 0}
		<p class="text-center text-sm text-text/50">No share links yet. Create one to get started.</p>
	{:else}
		{#each shareLinks.data as link (link.id)}
			{#if editingLinkId === link.id}
				<ShareLinkEdit
					{link}
					bind:permissions={editFormPermissions}
					bind:label={editFormLabel}
					bind:expiresAt={editFormExpiresAt}
					bind:allowAnonymous={editFormAllowAnonymous}
					onSave={() => handleUpdate(link.id)}
					onCancel={cancelEdit}
				/>
			{:else}
				<ShareLinkDisplay
					{link}
					onEdit={() => startEdit(link)}
					onDelete={() => handleDelete(link.id)}
					onCopy={() => copyLinkToClipboard(link.token)}
					onRotate={() => handleRotateToken(link.id)}
				/>
			{/if}
		{/each}
	{/if}
</div>
