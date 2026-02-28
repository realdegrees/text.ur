<script lang="ts">
	import { api } from '$api/client';
	import { goto, invalidate } from '$app/navigation';
	import { notification } from '$lib/stores/notificationStore';
	import LL from '$i18n/i18n-svelte';
	import { sessionStore } from '$lib/runes/session.svelte.js';
	import TagManagement from '$lib/components/TagManagement.svelte';
	import TaskManagement from '$lib/components/TaskManagement.svelte';
	import ConfirmButton from '$lib/components/ConfirmButton.svelte';
	import DangerZone from '$lib/components/DangerZone.svelte';
	import MarkdownTextEditor from '$lib/components/pdf/MarkdownTextEditor.svelte';
	import BackIcon from '~icons/material-symbols/arrow-back';
	import SaveIcon from '~icons/material-symbols/save-outline';
	import DeleteIcon from '~icons/material-symbols/delete-outline';
	import type { DocumentVisibility } from '$api/types';
	import { env } from '$env/dynamic/public';
	import { breadcrumbOverride } from '$lib/stores/breadcrumb.svelte';
	import { onDestroy } from 'svelte';

	let { data } = $props();
	let document = $derived(data.document);
	let group = $derived(data.membership.group);
	let activeTab = $state(0);

	const tabDefs = $derived([
		{ id: 'general', label: $LL.documentSettings.general() },
		{ id: 'tags', label: $LL.documentSettings.tagsTab() },
		{ id: 'tasks', label: $LL.documentSettings.tasksTab() }
	]);

	// Update breadcrumbs to include the active tab
	$effect(() => {
		const tab = tabDefs[activeTab];
		if (!tab) return;

		const baseCrumbs = data.breadcrumbs.filter((b: { href?: string }) => b.href);
		breadcrumbOverride.set([
			...baseCrumbs,
			{ label: $LL.documentSettings.title(), href: `#general` },
			{ label: tab.label }
		]);
	});

	onDestroy(() => {
		breadcrumbOverride.clear();
	});

	let documentName = $state(data.document.name);
	let documentDescription = $state(data.document.description ?? '');
	let documentVisibility = $state<DocumentVisibility>(data.document.visibility);
	let defaultMaxAttempts = $state(data.document.default_max_attempts);
	let isSaving = $state(false);
	let isClearing = $state(false);

	// Update local state when document data changes
	$effect(() => {
		documentName = document.name;
		documentDescription = document.description ?? '';
		documentVisibility = document.visibility;
		defaultMaxAttempts = document.default_max_attempts;
	});

	async function saveChanges() {
		if (!documentName.trim()) {
			notification('error', $LL.documentSettings.nameRequired());
			return;
		}

		isSaving = true;

		const result = await api.update(`/documents/${document.id}`, {
			name: documentName.trim(),
			description: documentDescription.trim() || null,
			visibility: documentVisibility,
			default_max_attempts: defaultMaxAttempts
		});

		isSaving = false;

		if (!result.success) {
			notification(result.error);
			return;
		}

		notification('success', $LL.documentSettings.updateSuccess());
		await invalidate('app:document');
		await invalidate('app:documents');
	}

	function hasChanges() {
		const descriptionChanged =
			(documentDescription.trim() || null) !== (document.description || null);
		return (
			documentName.trim() !== document.name ||
			documentVisibility !== document.visibility ||
			defaultMaxAttempts !== document.default_max_attempts ||
			descriptionChanged
		);
	}

	async function clearDocument() {
		isClearing = true;

		const result = await api.delete(`/documents/${document.id}/clear`);

		isClearing = false;

		if (!result.success) {
			notification(result.error);
			return;
		}

		notification('success', $LL.documentSettings.danger.clearSuccess());
		await invalidate('app:document');
	}
</script>

{#snippet generalTab()}
	<div class="flex flex-col gap-6">
		<!-- Document Name -->
		<div class="flex flex-col gap-2">
			<label for="document-name" class="form-label">{$LL.documents.documentName()}</label>
			<input
				id="document-name"
				type="text"
				bind:value={documentName}
				placeholder={$LL.documents.documentNamePlaceholder()}
				maxlength="255"
				class="form-input px-4"
			/>
		</div>

		<!-- Document Description -->
		<div class="flex flex-col gap-2">
			<label for="document-description" class="form-label">
				{$LL.documents.documentDescription()}
			</label>
			<MarkdownTextEditor
				bind:value={documentDescription}
				placeholder={$LL.documents.documentDescriptionPlaceholder()}
				rows={4}
				maxCommentLength={env.PUBLIC_DOCUMENT_DESCRIPTION_MAX_LENGTH
					? parseInt(env.PUBLIC_DOCUMENT_DESCRIPTION_MAX_LENGTH)
					: 5000}
			/>
			<p class="form-hint">
				{$LL.documents.documentDescriptionHint()}
			</p>
		</div>

		<!-- Document Visibility -->
		<div class="flex flex-col gap-2">
			<div class="form-label">{$LL.visibility.label()}</div>
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
							{$LL.visibility.public.label()}
						</label>
						<p class="form-hint">{$LL.documentSettings.publicDescription()}</p>
					</div>
				</div>

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
								{$LL.visibility.private.label()}
							</label>
							<p class="form-hint">{$LL.documentSettings.privateDescription()}</p>
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
					class="flex btn-primary flex-row items-center gap-2 px-6"
				>
					<SaveIcon class="h-5 w-5" />
					<span>{isSaving ? $LL.documentSettings.savingButton() : $LL.saveChanges()}</span>
				</button>
			</div>
		{/if}

		<!-- Danger Zone -->
		{#if sessionStore.validatePermissions(['administrator'])}
			<DangerZone
				title={$LL.documentSettings.danger.title()}
				description={$LL.documentSettings.danger.description()}
				actionLabel={$LL.documentSettings.danger.clearButton()}
			>
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
							<span
								>{isClearing
									? $LL.documentSettings.danger.clearing()
									: $LL.documentSettings.danger.clearButton()}</span
							>
						</button>
					{/snippet}
					{#snippet slideout()}
						<div class="rounded-md bg-red-500/10 px-3 py-2 text-red-500">
							{$LL.documentSettings.danger.confirmClear()}
						</div>
					{/snippet}
				</ConfirmButton>
			</DangerZone>
		{/if}
	</div>
{/snippet}

{#snippet tagsTab()}
	<TagManagement {document} />
{/snippet}

{#snippet tasksTab()}
	<!-- Default Max Attempts -->
	<div class="mb-6 flex flex-col gap-2">
		<label for="default-max-attempts" class="form-label">
			{$LL.documentSettings.defaultMaxAttempts()}
		</label>
		<input
			id="default-max-attempts"
			type="number"
			min="1"
			bind:value={defaultMaxAttempts}
			class="form-input w-24 px-4"
		/>
		<p class="form-hint">
			{$LL.documentSettings.defaultMaxAttemptsHint()}
		</p>
		{#if hasChanges()}
			<div class="flex flex-row justify-end gap-2">
				<button
					type="button"
					onclick={saveChanges}
					disabled={isSaving}
					class="flex btn-primary flex-row items-center gap-2 px-6"
				>
					<SaveIcon class="h-5 w-5" />
					<span>{isSaving ? $LL.documentSettings.savingButton() : $LL.saveChanges()}</span>
				</button>
			</div>
		{/if}
	</div>
	<TaskManagement {document} />
{/snippet}

<div class="flex h-full w-full flex-col">
	<!-- Document name + settings heading -->
	<div class="px-4 py-3">
		<h1 class="text-lg font-semibold">
			{document.name} - {$LL.documentSettings.title()}
		</h1>
	</div>

	<!-- Tab bar with back button -->
	{#if sessionStore.validatePermissions(['administrator'])}
		<nav class="flex flex-row items-center border-b border-text/20">
			<button
				onclick={() => goto(`/dashboard/groups/${group.id}/documents`)}
				class="px-3 py-2 text-text/70 transition-colors hover:text-text"
				aria-label={$LL.documentSettings.backToDocuments()}
			>
				<BackIcon class="h-5 w-5" />
			</button>
			{#each tabDefs as tab, index (tab.id)}
				<button
					onclick={() => {
						activeTab = index;
						history.replaceState(null, '', `#${tab.id}`);
					}}
					class="border-b-2 px-4 py-2 transition-all {activeTab === index
						? 'border-primary text-primary'
						: 'border-transparent text-text/70 hover:border-text/30 hover:text-text'}"
				>
					{tab.label}
				</button>
			{/each}
		</nav>

		<div class="flex-1 overflow-auto p-6">
			{@render [generalTab, tagsTab, tasksTab][activeTab]()}
		</div>
	{:else}
		<div class="flex-1 overflow-auto p-6">
			{@render generalTab()}
		</div>
	{/if}
</div>
