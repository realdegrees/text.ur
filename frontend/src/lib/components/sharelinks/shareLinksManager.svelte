<script lang="ts">
	import AddIcon from '~icons/material-symbols/add-2-rounded';
	import { api } from '$api/client';
	import { notification } from '$lib/stores/notificationStore';
	import { invalidate } from '$app/navigation';
	import LL from '$i18n/i18n-svelte';
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
			expires_at: createFormExpiresAt ? new Date(createFormExpiresAt).toISOString() : null,
			allow_anonymous_access: createFormAllowAnonymous
		};

		const result = await api.post(`/groups/${groupId}/sharelinks`, createData);

		if (result.success) {
			notification('success', $LL.sharelinks.created());
			resetCreateForm();
			await invalidate('app:sharelinks');
		} else {
			notification(result.error);
		}
	}

	async function handleUpdate(linkId: number) {
		const updateData: ShareLinkUpdate = {
			permissions: editFormPermissions,
			label: editFormLabel || null,
			expires_at: editFormExpiresAt ? new Date(editFormExpiresAt).toISOString() : null,
			allow_anonymous_access: editFormAllowAnonymous,
			rotate_token: null
		};

		const result = await api.update(`/groups/${groupId}/sharelinks/${linkId}`, updateData);

		if (result.success) {
			notification('success', $LL.sharelinks.updated());
			cancelEdit();
			await invalidate('app:sharelinks');
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
			notification('success', $LL.sharelinks.rotated());
			await invalidate('app:sharelinks');
		} else {
			notification(result.error);
		}
	}

	async function handleDelete(linkId: number) {
		const confirmed = confirm($LL.sharelinks.deleteConfirm());
		if (!confirmed) return;

		const result = await api.delete(`/groups/${groupId}/sharelinks/${linkId}`);

		if (result.success) {
			notification('success', $LL.sharelinks.deleted());
			await invalidate('app:sharelinks');
		} else {
			notification(result.error);
		}
	}

	async function copyLinkToClipboard(token: string) {
		const link = `${window.location.origin}/sharelink/${token}`;
		try {
			await navigator.clipboard.writeText(link);
			notification('success', $LL.sharelinks.linkCopied());
		} catch {
			notification('error', $LL.sharelinks.copyFailed());
		}
	}
</script>

<div class="flex flex-col gap-4">
	<!-- Header -->
	<div class="flex items-center justify-between">
		{#if !showCreateForm}
			<button
				type="button"
				onclick={() => (showCreateForm = true)}
				class="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-text transition-all hover:bg-primary/80"
			>
				<AddIcon class="h-5 w-5" />
				<p>{$LL.sharelinks.createLink()}</p>
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
		<p class="text-center text-sm text-text/50">{$LL.sharelinks.noLinksYet()}</p>
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
