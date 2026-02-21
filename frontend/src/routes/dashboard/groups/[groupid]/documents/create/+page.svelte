<script lang="ts">
	import type { DocumentCreate, DocumentRead, Visibility } from '$api/types';
	import { visibilitySchema } from '$api/schemas';
	import { goto } from '$app/navigation';
	import { api } from '$api/client';
	import { env } from '$env/dynamic/public';
	import LL from '$i18n/i18n-svelte';
	import UploadIcon from '~icons/material-symbols/upload-file-outline';
	import DocumentIcon from '~icons/material-symbols/description-outline';
	import Loading from '~icons/svg-spinners/90-ring-with-bg';
	import DeleteIcon from '~icons/material-symbols/delete-outline';
	import DragDropIcon from '~icons/material-symbols/upload-file';
	import InfoIcon from '~icons/material-symbols/info-outline';
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
	let selectedVisibility: Visibility = $state('public');
	let isLoading: boolean = $state(false);
	let errorMessage: string = $state('');
	let isDragging: boolean = $state(false);
	let documentName: string = $state('');
	let documentDescription: string = $state('');

	const visibilityOptions = $derived(
		visibilitySchema.options.map((option) => ({
			value: option.value,
			label: $LL.visibility[option.value].label(),
			description: $LL.visibility[option.value].description()
		}))
	);

	function validateFile(file: File): string | null {
		if (file.type !== ALLOWED_FILE_TYPE) {
			return $LL.documents.invalidFileType();
		}
		if (file.size > MAX_FILE_SIZE_BYTES) {
			return $LL.documents.fileTooLarge({ max: MAX_FILE_SIZE_MB, actual: (file.size / (1024 * 1024)).toFixed(2) });
		}
		return null;
	}

	function handleFileSelect(event: Event): void {
		const input = event.target as HTMLInputElement;
		if (input.files && input.files.length > 0) {
			const file = input.files[0];
			const validationError = validateFile(file);
			if (validationError) {
				errorMessage = validationError;
				selectedFile = null;
			} else {
				selectedFile = file;
				errorMessage = '';
			}
		}
	}

	function handleDragOver(event: DragEvent): void {
		event.preventDefault();
		isDragging = true;
	}

	function handleDragLeave(event: DragEvent): void {
		event.preventDefault();
		isDragging = false;
	}

	function handleDrop(event: DragEvent): void {
		event.preventDefault();
		isDragging = false;

		if (event.dataTransfer?.files && event.dataTransfer.files.length > 0) {
			const file = event.dataTransfer.files[0];
			const validationError = validateFile(file);
			if (validationError) {
				errorMessage = validationError;
				selectedFile = null;
			} else {
				selectedFile = file;
				errorMessage = '';
			}
		}
	}

	function clearFile(): void {
		selectedFile = null;
		errorMessage = '';
	}

	function formatFileSize(bytes: number): string {
		const mb = bytes / (1024 * 1024);
		return `${mb.toFixed(2)} MB`;
	}

	async function handleSubmit(event: Event): Promise<void> {
		event.preventDefault();

		if (!selectedFile) {
			errorMessage = $LL.documents.selectFile();
			return;
		}

		const validationError = validateFile(selectedFile);
		if (validationError) {
			errorMessage = validationError;
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
			<div
				class="rounded-md border border-red-300 bg-red-100 p-3 text-red-700 dark:border-red-700 dark:bg-red-900/30 dark:text-red-300"
			>
				{errorMessage}
			</div>
		{/if}

		<!-- File Upload Section -->
		<div class="flex flex-col gap-2">
			<div class="text-sm font-semibold text-text/70">{$LL.documents.documentFile()}</div>
			<p class="text-xs text-text/50">
				{$LL.documents.documentFileHint({ size: MAX_FILE_SIZE_MB })}
			</p>

			{#if !selectedFile}
				<!-- Drag and Drop Area -->
				<div
					role="button"
					tabindex="0"
					class="relative rounded-lg border-2 border-dashed transition-colors {isDragging
						? 'border-primary bg-primary/10'
						: 'border-text/20 bg-text/5'}"
					ondragover={handleDragOver}
					ondragleave={handleDragLeave}
					ondrop={handleDrop}
				>
					<input
						type="file"
						id="fileInput"
						accept={ALLOWED_FILE_TYPE}
						onchange={handleFileSelect}
						class="absolute inset-0 cursor-pointer opacity-0"
						disabled={isLoading}
					/>
					<div class="flex flex-col items-center gap-4 p-8">
						<DragDropIcon class="h-16 w-16 text-text/40" />
						<div class="flex flex-col items-center gap-2">
							<p class="text-lg font-semibold">{$LL.documents.dragDrop()}</p>
							<p class="text-sm text-text/60">{$LL.documents.orClickBrowse()}</p>
						</div>
						<p class="text-xs text-text/50">{$LL.documents.maxFileSize({ size: MAX_FILE_SIZE_MB })}</p>
					</div>
				</div>
			{:else}
				<!-- Selected File Display -->
				<div
					class="flex flex-row items-center gap-4 rounded-lg border border-text/20 bg-text/5 p-4"
				>
					<DocumentIcon class="h-8 w-8 text-primary" />
					<div class="flex flex-1 flex-col gap-1">
						<p class="font-semibold">{selectedFile.name}</p>
						<p class="text-sm text-text/60">{formatFileSize(selectedFile.size)}</p>
					</div>
					<button
						type="button"
						onclick={clearFile}
						class="rounded-md bg-red-500/10 p-2 text-red-500 transition-all hover:bg-red-500/20"
						disabled={isLoading}
					>
						<DeleteIcon class="h-5 w-5" />
					</button>
				</div>
			{/if}
		</div>

		<!-- Document Name Field -->
		<div class="flex flex-col gap-2">
			<label for="documentName" class="text-sm font-semibold text-text/70">{$LL.documents.documentName()}</label>
			<input
				type="text"
				id="documentName"
				bind:value={documentName}
				placeholder={$LL.documents.documentNamePlaceholder()}
				class="rounded-lg border border-text/20 bg-inset p-3 text-sm shadow-inner focus:border-primary focus:ring-1 focus:ring-primary"
				required
			/>
		</div>

		<!-- Document Description Field -->
		<div class="flex flex-col gap-2">
			<label for="documentDescription" class="text-sm font-semibold text-text/70">
				{$LL.documents.documentDescription()}
			</label>
			<MarkdownTextEditor
				bind:value={documentDescription}
				placeholder={$LL.documents.documentDescriptionPlaceholder()}
				rows={4}
				maxCommentLength={5000}
			/>
			<p class="text-xs text-text/50">
				{$LL.documents.documentDescriptionHint()}
			</p>
		</div>

		<!-- Visibility Section -->
		<div class="flex flex-col gap-2">
			<div class="text-sm font-semibold text-text/70">{$LL.visibility.settings()}</div>
			<p class="text-xs text-text/50">{$LL.visibility.chooseHint()}</p>

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
		{#if sessionStore.validatePermissions(['manage_tags'])}
			<div class="rounded-lg border border-primary/30 bg-primary/5 p-4">
				<div class="flex items-start gap-3">
					<InfoIcon class="h-5 w-5 shrink-0 text-primary" />
					<div class="flex flex-col gap-1">
						<p class="font-semibold text-primary">{$LL.documents.tagInfo.title()}</p>
						<p class="text-sm text-text/80">
							{$LL.documents.tagInfo.description()}
						</p>
						<p class="text-xs text-text/60">
							{$LL.documents.tagInfo.hint()}
						</p>
					</div>
				</div>
			</div>
		{/if}

		<!-- Submit Button -->
		<div class="flex flex-row justify-end gap-2">
			<a
				href="/dashboard/groups/{groupId}/documents"
				class="rounded-md bg-text/10 px-6 py-2 transition-all hover:bg-text/20"
			>
				{$LL.cancel()}
			</a>
			<button
				type="submit"
				disabled={isLoading || !selectedFile}
				class="flex flex-row items-center gap-2 rounded-md bg-primary px-6 py-2 text-text transition-all hover:bg-primary/80 disabled:cursor-not-allowed disabled:bg-text/30"
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
