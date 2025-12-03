<script lang="ts">
	import { api } from '$api/client';
	import { goto, invalidateAll } from '$app/navigation';
	import { notification } from '$lib/stores/notificationStore';
	import { sessionStore } from '$lib/runes/session.svelte.js';
	import TagManagement from '$lib/components/TagManagement.svelte';
	import ConfirmButton from '$lib/components/ConfirmButton.svelte';
	import BackIcon from '~icons/material-symbols/arrow-back';
	import SaveIcon from '~icons/material-symbols/save-outline';
	import DeleteIcon from '~icons/material-symbols/delete-outline';
	import type { Visibility } from '$api/types';

	let { data } = $props();
	let document = $derived(data.document);
	let group = $derived(data.membership.group);

	let documentName = $derived(document.name);
	let documentVisibility = $derived<Visibility>(document.visibility);
	let isSaving = $state(false);
	let isClearing = $state(false);

	async function saveChanges() {
		if (!documentName.trim()) {
			notification('error', 'Document name is required');
			return;
		}

		isSaving = true;

		const result = await api.update(`/documents/${document.id}`, {
			name: documentName.trim(),
			visibility: documentVisibility
		});

		isSaving = false;

		if (!result.success) {
			notification(result.error);
			return;
		}

		notification('success', 'Document updated successfully');
		await invalidateAll();
	}

	function hasChanges() {
		return documentName.trim() !== document.name || documentVisibility !== document.visibility;
	}

	async function clearDocument() {
		isClearing = true;

		const result = await api.delete(`/documents/${document.id}/clear`);

		isClearing = false;

		if (!result.success) {
			notification(result.error);
			return;
		}

		notification('success', 'All comments cleared successfully');
		await invalidateAll();
	}
</script>

<div class="flex h-full w-full flex-col gap-6 p-6">
	<!-- Header -->
	<div class="flex items-center gap-3">
		<button
			onclick={() => goto(`/dashboard/groups/${group.id}/documents`)}
			class="rounded p-2 transition hover:bg-text/10"
			aria-label="Back to documents"
		>
			<BackIcon class="h-5 w-5" />
		</button>
		<h1 class="text-2xl font-bold">Document Settings</h1>
	</div>

	<!-- Settings Form -->
	<div class="flex flex-col gap-6">
		<!-- Document Name -->
		<div class="flex flex-col gap-2">
			<label for="document-name" class="text-sm font-semibold text-text/70">Document Name</label>
			<input
				id="document-name"
				type="text"
				bind:value={documentName}
				placeholder="Enter document name"
				maxlength="255"
				class="rounded-md border border-text/20 bg-text/5 px-4 py-2 transition-colors focus:border-text/50 focus:outline-none"
			/>
		</div>

		<!-- Document Visibility -->
		<div class="flex flex-col gap-2">
			<div class="text-sm font-semibold text-text/70">Visibility</div>
			<div class="flex flex-col gap-3">
				<div class="flex items-start gap-2">
					<input
						type="radio"
						id="visibility-public"
						value="public"
						bind:group={documentVisibility}
						class="mt-0.5 cursor-pointer"
					/>
					<div class="flex flex-col gap-0.5">
						<label for="visibility-public" class="cursor-pointer text-sm font-medium">
							Public
						</label>
						<p class="text-xs text-text/50">All group members can view this document</p>
					</div>
				</div>

				{#if sessionStore.validatePermissions(['view_restricted_documents'])}
					<div class="flex items-start gap-2">
						<input
							type="radio"
							id="visibility-restricted"
							value="restricted"
							bind:group={documentVisibility}
							class="mt-0.5 cursor-pointer"
						/>
						<div class="flex flex-col gap-0.5">
							<label for="visibility-restricted" class="cursor-pointer text-sm font-medium">
								Restricted
							</label>
							<p class="text-xs text-text/50">
								Only members with VIEW_RESTRICTED_DOCUMENTS permission can view
							</p>
						</div>
					</div>
				{/if}

				{#if sessionStore.validatePermissions(['administrator'])}
					<div class="flex items-start gap-2">
						<input
							type="radio"
							id="visibility-private"
							value="private"
							bind:group={documentVisibility}
							class="mt-0.5 cursor-pointer"
						/>
						<div class="flex flex-col gap-0.5">
							<label for="visibility-private" class="cursor-pointer text-sm font-medium">
								Private
							</label>
							<p class="text-xs text-text/50">Only administrators can view this document</p>
						</div>
					</div>
				{/if}
			</div>
		</div>

		<!-- Save Button -->
		{#if hasChanges()}
			<div class="flex flex-row justify-end gap-2">
				<button
					type="button"
					onclick={saveChanges}
					disabled={isSaving}
					class="flex flex-row items-center gap-2 rounded-md bg-primary px-6 py-2 text-text transition-all hover:bg-primary/80 disabled:cursor-not-allowed disabled:opacity-50"
				>
					<SaveIcon class="h-5 w-5" />
					<span>{isSaving ? 'Saving...' : 'Save Changes'}</span>
				</button>
			</div>
		{/if}

		<!-- Tag Management -->
		{#if sessionStore.validatePermissions(['manage_tags'])}
			<div class="flex flex-col gap-2">
				<TagManagement {document} />
			</div>
		{/if}

		<!-- Danger Zone -->
		{#if sessionStore.validatePermissions(['administrator'])}
			<div class="mt-8 flex flex-col gap-4 rounded-md border border-red-500/30 bg-red-500/5 p-4">
				<h2 class="text-lg font-semibold text-red-500">Danger Zone</h2>
				<p class="text-sm text-text/70">
					Permanently delete all comments and annotations from this document. This action cannot be
					undone.
				</p>

				<ConfirmButton disabled={isClearing} onConfirm={clearDocument}>
					{#snippet button(isOpen)}
						<button
							type="button"
							class="flex w-fit flex-row items-center gap-2 rounded-md transition-all {isOpen
								? 'bg-red-500/30 hover:bg-red-500/40'
								: 'bg-red-500/20 hover:bg-red-500/30'} {isClearing
								? 'cursor-not-allowed opacity-50'
								: ''} px-4 py-2"
							disabled={isClearing}
						>
							<DeleteIcon class="h-5 w-5" />
							<span>{isClearing ? 'Clearing...' : 'Clear All Comments'}</span>
						</button>
					{/snippet}
					{#snippet slideout()}
						<div class="rounded-md bg-red-500/10 px-3 py-2 text-red-500">Confirm Clear</div>
					{/snippet}
				</ConfirmButton>
			</div>
		{/if}
	</div>
</div>
