<script lang="ts">
	import DragDropIcon from '~icons/material-symbols/upload-file';
	import DocumentIcon from '~icons/material-symbols/description-outline';
	import DeleteIcon from '~icons/material-symbols/delete-outline';
	import LL from '$i18n/i18n-svelte';

	let {
		value = $bindable<File | null>(null),
		errorMessage = $bindable(''),
		accept,
		maxSizeBytes,
		maxSizeMB,
		disabled = false
	}: {
		value: File | null;
		errorMessage: string;
		accept: string;
		maxSizeBytes: number;
		maxSizeMB: number;
		disabled?: boolean;
	} = $props();

	let isDragging: boolean = $state(false);

	function validateFile(file: File): string | null {
		if (file.type !== accept) {
			return $LL.documents.invalidFileType();
		}
		if (file.size > maxSizeBytes) {
			return $LL.documents.fileTooLarge({
				max: maxSizeMB,
				actual: (file.size / (1024 * 1024)).toFixed(2)
			});
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
				value = null;
			} else {
				value = file;
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
				value = null;
			} else {
				value = file;
				errorMessage = '';
			}
		}
	}

	function clearFile(): void {
		value = null;
		errorMessage = '';
	}

	function formatFileSize(bytes: number): string {
		const mb = bytes / (1024 * 1024);
		return `${mb.toFixed(2)} MB`;
	}
</script>

{#if !value}
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
			{accept}
			onchange={handleFileSelect}
			class="absolute inset-0 cursor-pointer opacity-0"
			{disabled}
		/>
		<div class="flex flex-col items-center gap-4 p-8">
			<DragDropIcon class="h-16 w-16 text-text/40" />
			<div class="flex flex-col items-center gap-2">
				<p class="text-lg font-semibold">{$LL.documents.dragDrop()}</p>
				<p class="text-sm text-text/60">{$LL.documents.orClickBrowse()}</p>
			</div>
			<p class="text-xs text-text/50">
				{$LL.documents.maxFileSize({ size: maxSizeMB })}
			</p>
		</div>
	</div>
{:else}
	<!-- Selected File Display -->
	<div class="flex flex-row items-center gap-4 rounded-lg border border-text/20 bg-text/5 p-4">
		<DocumentIcon class="h-8 w-8 text-primary" />
		<div class="flex flex-1 flex-col gap-1">
			<p class="font-semibold">{value.name}</p>
			<p class="text-sm text-text/60">{formatFileSize(value.size)}</p>
		</div>
		<button
			type="button"
			onclick={clearFile}
			class="rounded-md bg-red-500/10 p-2 text-red-500 transition-all hover:bg-red-500/20"
			{disabled}
		>
			<DeleteIcon class="h-5 w-5" />
		</button>
	</div>
{/if}
