<script lang="ts">
	import type { DocumentCreate, DocumentRead, DocumentVisibility } from '$api/types';
	import { documentVisibilitySchema } from '$api/schemas';
	import { goto } from '$app/navigation';
	import { api } from '$api/client';
	import { env } from '$env/dynamic/public';
	import LL from '$i18n/i18n-svelte';
	import UploadIcon from '~icons/material-symbols/upload-file-outline';
	import Loading from '~icons/svg-spinners/90-ring-with-bg';
	import InfoBanner from '$lib/components/InfoBanner.svelte';
	import FileUpload from '$lib/components/FileUpload.svelte';
	import { notification } from '$lib/stores/notificationStore.js';
	import { sessionStore } from '$lib/runes/session.svelte.js';
	import MarkdownTextEditor from '$lib/components/pdf/MarkdownTextEditor.svelte';

	const MAX_FILE_SIZE_MB: number = env.PUBLIC_MAX_UPLOAD_SIZE_MB
		? parseInt(env.PUBLIC_MAX_UPLOAD_SIZE_MB)
		: 50;
	const MAX_FILE_SIZE_BYTES: number = MAX_FILE_SIZE_MB * 1024 * 1024;
	const ALLOWED_FILE_TYPE: string = 'application/pdf';

	const { data } = $props();
	const groupId = $derived(data.membership.group.id);

	let selectedFile: File | null = $state(null);
	let selectedVisibility: DocumentVisibility = $state('public');
	let isLoading: boolean = $state(false);
	let errorMessage: string = $state('');
	let documentName: string = $state('');
	let documentDescription: string = $state('');

	const visibilityOptions = $derived(
		documentVisibilitySchema.options.map((option) => ({
			value: option.value,
			label: $LL.visibility[option.value].label(),
			description: $LL.visibility[option.value].description()
		}))
	);

	async function handleSubmit(event: Event): Promise<void> {
		event.preventDefault();

		if (!selectedFile) {
			errorMessage = $LL.documents.selectFile();
			return;
		}

		isLoading = true;

		const formData = new FormData();
		formData.append('file', selectedFile);

		const documentData: DocumentCreate = {
			visibility: selectedVisibility,
			group_id: groupId,
			name: documentName,
			description: documentDescription.trim() || null
		};

		formData.append('data', JSON.stringify(documentData));
		formData.append('name', documentName);

		const result = await api.post<DocumentRead>('/documents', formData);

		isLoading = false;

		if (!result.success) {
			notification(result.error);
			return;
		}

		if (!result.data) {
			notification('error', $LL.documents.uploadFailed());
			return;
		}

		notification('success', $LL.documents.uploadSuccess());
		goto(`/dashboard/groups/${groupId}/documents`, { invalidateAll: true });
	}
</script>

<div class="flex h-full w-full flex-col gap-6 p-6">
	<h1 class="text-2xl font-bold">{$LL.documents.uploadDocument()}</h1>

	<!-- Form Section -->
	<form onsubmit={handleSubmit} class="flex flex-col gap-6">
		<!-- Error Message -->
		{#if errorMessage}
			<InfoBanner variant="error">{errorMessage}</InfoBanner>
		{/if}

		<!-- File Upload Section -->
		<div class="flex flex-col gap-2">
			<div class="form-label">{$LL.documents.documentFile()}</div>
			<p class="form-hint">
				{$LL.documents.documentFileHint({ size: MAX_FILE_SIZE_MB })}
			</p>

			<FileUpload
				bind:value={selectedFile}
				bind:errorMessage
				accept={ALLOWED_FILE_TYPE}
				maxSizeBytes={MAX_FILE_SIZE_BYTES}
				maxSizeMB={MAX_FILE_SIZE_MB}
				disabled={isLoading}
			/>
		</div>

		<!-- Document Name Field -->
		<div class="flex flex-col gap-2">
			<label for="documentName" class="form-label">{$LL.documents.documentName()}</label>
			<input
				type="text"
				id="documentName"
				bind:value={documentName}
				placeholder={$LL.documents.documentNamePlaceholder()}
				class="form-input"
				required
			/>
		</div>

		<!-- Document Description Field -->
		<div class="flex flex-col gap-2">
			<label for="documentDescription" class="form-label">
				{$LL.documents.documentDescription()}
			</label>
			<MarkdownTextEditor
				bind:value={documentDescription}
				placeholder={$LL.documents.documentDescriptionPlaceholder()}
				rows={4}
				maxCommentLength={5000}
			/>
			<p class="form-hint">
				{$LL.documents.documentDescriptionHint()}
			</p>
		</div>

		<!-- Visibility Section -->
		<div class="flex flex-col gap-2">
			<div class="form-label">{$LL.visibility.settings()}</div>
			<p class="form-hint">{$LL.visibility.chooseHint()}</p>

			<div class="flex flex-col gap-2">
				{#each visibilityOptions as option (option.value)}
					{@const isSelected = selectedVisibility === option.value}
					<label
						class="flex cursor-pointer flex-row items-start gap-3 rounded-lg bg-inset p-4 transition-all hover:bg-text/10"
						style={isSelected ? 'background-color: rgba(var(--primary-rgb), 0.1);' : ''}
					>
						<input
							type="radio"
							name="visibility"
							value={option.value}
							checked={isSelected}
							onchange={() => (selectedVisibility = option.value)}
							class="mt-1 h-4 w-4 shrink-0"
							disabled={isLoading}
						/>
						<div class="flex flex-col gap-1">
							<span class="font-semibold">{option.label}</span>
							<span class="text-sm text-text/70">{option.description}</span>
						</div>
					</label>
				{/each}
			</div>
		</div>

		<!-- Tag Management Info -->
		{#if sessionStore.validatePermissions(['administrator'])}
			<InfoBanner variant="info" title={$LL.documents.tagInfo.title()}>
				<p class="text-sm text-text/80">
					{$LL.documents.tagInfo.description()}
				</p>
				<p class="form-hint">
					{$LL.documents.tagInfo.hint()}
				</p>
			</InfoBanner>
		{/if}

		<!-- Submit Button -->
		<div class="flex flex-row justify-end gap-2">
			<a href="/dashboard/groups/{groupId}/documents" class="btn-secondary">
				{$LL.cancel()}
			</a>
			<button
				type="submit"
				disabled={isLoading || !selectedFile}
				class="flex btn-primary flex-row items-center gap-2"
			>
				{#if isLoading}
					<Loading class="h-5 w-5" />
					<span>{$LL.uploading()}</span>
				{:else}
					<UploadIcon class="h-5 w-5" />
					<span>{$LL.documents.uploadDocument()}</span>
				{/if}
			</button>
		</div>
	</form>
</div>
