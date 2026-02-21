<script lang="ts">
	import { api } from '$api/client';
	import type { DocumentRead, TagRead } from '$api/types';
	import { notification } from '$lib/stores/notificationStore';
	import { invalidate } from '$app/navigation';
	import LL from '$i18n/i18n-svelte';
	import AddIcon from '~icons/material-symbols/add-2-rounded';
	import EditIcon from '~icons/material-symbols/edit-outline';
	import DeleteIcon from '~icons/material-symbols/delete-outline';
	import SaveIcon from '~icons/material-symbols/save-outline';
	import CancelIcon from '~icons/material-symbols/cancel-outline';
	import ConfirmButton from '$lib/components/ConfirmButton.svelte';

	interface Props {
		document: DocumentRead;
	}

	let { document }: Props = $props();

	let tags = $derived(document.tags || []);
	let isAddingTag = $state(false);
	let editingTagId = $state<number | null>(null);
	let activeColorPicker = $state<'new' | 'edit' | null>(null);

	// New tag form state
	let newTag = $state({
		label: '',
		description: '',
		color: '#3B82F6' // Default blue color
	});

	function handleClickOutside(event: MouseEvent) {
		const target = event.target as HTMLElement;
		if (!target.closest('[data-color-picker]')) {
			activeColorPicker = null;
		}
	}

	// Edit tag form state
	let editTag = $state<{ label: string; description: string; color: string }>({
		label: '',
		description: '',
		color: ''
	});

	async function createTag() {
		if (!newTag.label.trim()) {
			notification('error', $LL.tags.labelRequired());
			return;
		}

		const result = await api.post<TagRead>(`/documents/${document.id}/tags`, {
			label: newTag.label.trim(),
			description: newTag.description.trim() || null,
			color: newTag.color
		});

		if (!result.success) {
			notification(result.error);
			return;
		}

		notification('success', $LL.tags.createSuccess());
		resetNewTagForm();
		await invalidate('app:document');
	}

	async function updateTag(tagId: number) {
		if (!editTag.label.trim()) {
			notification('error', $LL.tags.labelRequired());
			return;
		}

		const result = await api.update(`/documents/${document.id}/tags/${tagId}`, {
			label: editTag.label.trim(),
			description: editTag.description.trim() || null,
			color: editTag.color
		});

		if (!result.success) {
			notification(result.error);
			return;
		}

		notification('success', $LL.tags.updateSuccess());
		editingTagId = null;
		await invalidate('app:document');
	}

	async function deleteTag(tagId: number) {
		const result = await api.delete(`/documents/${document.id}/tags/${tagId}`);

		if (!result.success) {
			notification(result.error);
			return;
		}

		notification('success', $LL.tags.deleteSuccess());
		await invalidate('app:document');
	}

	function startEditingTag(tag: TagRead) {
		editingTagId = tag.id;
		editTag = {
			label: tag.label,
			description: tag.description || '',
			color: tag.color
		};
	}

	function cancelEdit() {
		editingTagId = null;
		editTag = { label: '', description: '', color: '' };
		activeColorPicker = null;
	}

	function resetNewTagForm() {
		isAddingTag = false;
		newTag = {
			label: '',
			description: '',
			color: '#3B82F6'
		};
		activeColorPicker = null;
	}

	function hslToHex(h: number, s: number, l: number): string {
		l /= 100;
		const a = (s * Math.min(l, 1 - l)) / 100;
		const f = (n: number) => {
			const k = (n + h / 30) % 12;
			const color = l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
			return Math.round(255 * color)
				.toString(16)
				.padStart(2, '0');
		};
		return `#${f(0)}${f(8)}${f(4)}`;
	}

	function hexToHue(hex: string): number {
		const r = parseInt(hex.slice(1, 3), 16) / 255;
		const g = parseInt(hex.slice(3, 5), 16) / 255;
		const b = parseInt(hex.slice(5, 7), 16) / 255;

		const max = Math.max(r, g, b);
		const min = Math.min(r, g, b);
		const delta = max - min;

		if (delta === 0) return 0;

		let hue = 0;
		if (max === r) {
			hue = ((g - b) / delta) % 6;
		} else if (max === g) {
			hue = (b - r) / delta + 2;
		} else {
			hue = (r - g) / delta + 4;
		}

		hue = Math.round(hue * 60);
		return hue < 0 ? hue + 360 : hue;
	}
</script>

{#snippet tagForm(
	formData: { label: string; description: string; color: string },
	isEdit: boolean,
	tagId?: number
)}
	<div class="grid grid-cols-1 gap-3 md:grid-cols-2">
		<div class="flex flex-col gap-1.5">
			<label
				for={isEdit ? `edit-tag-label-${tagId}` : 'new-tag-label'}
				class="text-xs font-semibold text-text/70">{$LL.tags.label()}</label
			>
			<input
				id={isEdit ? `edit-tag-label-${tagId}` : 'new-tag-label'}
				type="text"
				bind:value={formData.label}
				placeholder={isEdit ? $LL.tags.tagLabelEditPlaceholder() : $LL.tags.tagLabelPlaceholder()}
				maxlength="50"
				class="rounded-md border border-text/20 bg-text/5 px-3 py-2 text-sm transition-colors outline-none focus:border-text/50"
			/>
		</div>
		<div class="flex flex-col gap-1.5">
			<label
				for={isEdit ? `edit-tag-color-${tagId}` : 'new-tag-color'}
				class="text-xs font-semibold text-text/70">{$LL.tags.color()}</label
			>
			<div class="relative" data-color-picker>
				<button
					type="button"
					aria-label={isEdit ? $LL.tags.chooseColor() : $LL.tags.chooseColorNew()}
					onclick={() =>
						(activeColorPicker =
							activeColorPicker === (isEdit ? 'edit' : 'new') ? null : isEdit ? 'edit' : 'new')}
					class="flex w-fit items-center gap-2 rounded-md border border-text/20 bg-text/5 px-3 py-2 transition hover:border-text/30"
				>
					<div
						class="h-6 w-6 rounded border border-text/20"
						style="background-color: {formData.color};"
					></div>
				</button>
				{#if activeColorPicker === (isEdit ? 'edit' : 'new')}
					<div
						class="bg-bg absolute top-full left-0 z-10 mt-2 flex flex-col gap-2 rounded-md border border-text/20 bg-inset p-3 shadow-lg"
					>
						<input
							id={isEdit ? `edit-tag-color-${tagId}` : 'new-tag-color'}
							type="range"
							min="0"
							max="360"
							value={hexToHue(formData.color)}
							oninput={(e) => {
								const hue = (e.target as HTMLInputElement).value;
								formData.color = hslToHex(parseInt(hue), 70, 55);
							}}
							class="h-2 w-48 cursor-pointer appearance-none rounded-lg"
							style="background: linear-gradient(to right, #ff0000 0%, #ffff00 17%, #00ff00 33%, #00ffff 50%, #0000ff 67%, #ff00ff 83%, #ff0000 100%);"
						/>
					</div>
				{/if}
			</div>
		</div>
		<div class="flex flex-col gap-1.5 md:col-span-2">
			<label
				for={isEdit ? `edit-tag-description-${tagId}` : 'new-tag-description'}
				class="text-xs font-semibold text-text/70">{$LL.tags.description()}</label
			>
			<textarea
				id={isEdit ? `edit-tag-description-${tagId}` : 'new-tag-description'}
				bind:value={formData.description}
				placeholder={$LL.tags.descriptionPlaceholder()}
				maxlength="200"
				rows="2"
				class="rounded-md border border-text/20 bg-text/5 px-3 py-2 text-sm transition-colors outline-none focus:border-text/50"
			></textarea>
		</div>
	</div>
{/snippet}

<svelte:body onclick={handleClickOutside} />

<div class="flex flex-col gap-4">
	<div class="flex items-center justify-between">
		<div class="text-sm font-semibold text-text/70">{$LL.tags.title()}</div>
		<button
			onclick={() => (isAddingTag = !isAddingTag)}
			class="flex items-center gap-2 rounded-md bg-primary/20 px-3 py-2 text-sm font-semibold transition hover:bg-primary/30"
		>
			<AddIcon class="h-4 w-4" />
			{$LL.tags.addTag()}
		</button>
	</div>

	<!-- Add Tag Form -->
	{#if isAddingTag}
		<div class="flex flex-col gap-3 rounded-md border border-text/20 bg-text/5 p-4">
			<div class="text-sm font-semibold">{$LL.tags.newTag()}</div>
			{@render tagForm(newTag, false)}
			<div class="flex items-center gap-2">
				<button
					onclick={createTag}
					class="flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-semibold transition hover:bg-primary/80"
				>
					<SaveIcon class="h-4 w-4" />
					{$LL.tags.createTag()}
				</button>
				<button
					onclick={resetNewTagForm}
					class="flex items-center gap-2 rounded-md bg-text/10 px-3 py-2 text-sm font-semibold transition hover:bg-text/20"
				>
					<CancelIcon class="h-4 w-4" />
					{$LL.cancel()}
				</button>
			</div>
		</div>
	{/if}

	<!-- Tags List -->
	<div class="flex flex-col gap-2">
		{#if tags.length === 0}
			<p class="text-sm text-text/50">{$LL.tags.noTags()}</p>
		{:else}
			{#each tags as tag (tag.id)}
				{#if editingTagId === tag.id}
					<!-- Edit Form -->
					<div class="flex flex-col gap-3 rounded-md border border-text/20 bg-text/5 p-4">
						<div class="text-sm font-semibold">{$LL.tags.editTag()}</div>
						{@render tagForm(editTag, true, tag.id)}
						<div class="flex items-center gap-2">
							<button
								onclick={() => updateTag(tag.id)}
								class="flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-semibold transition hover:bg-primary/80"
							>
								<SaveIcon class="h-4 w-4" />
								{$LL.saveChanges()}
							</button>
							<button
								onclick={cancelEdit}
								class="flex items-center gap-2 rounded-md bg-text/10 px-3 py-2 text-sm font-semibold transition hover:bg-text/20"
							>
								<CancelIcon class="h-4 w-4" />
								{$LL.cancel()}
							</button>
						</div>
					</div>
				{:else}
					<!-- Tag Display -->
					<div
						class="flex items-center gap-3 rounded-md border border-text/20 bg-text/5 p-3 transition hover:border-text/30"
					>
						<div
							class="h-8 w-8 shrink-0 rounded-md border border-text/20"
							style="background-color: {tag.color};"
						></div>
						<div class="flex-1">
							<p class="text-sm font-semibold">{tag.label}</p>
							{#if tag.description}
								<p class="text-xs text-text/50">{tag.description}</p>
							{/if}
						</div>
						<div class="flex items-center gap-1">
							<button
								onclick={() => startEditingTag(tag)}
								class="rounded-md p-1.5 transition hover:bg-text/10"
								aria-label={$LL.tags.editAriaLabel()}
							>
								<EditIcon class="h-4 w-4" />
							</button>
							<ConfirmButton onConfirm={() => deleteTag(tag.id)}>
								{#snippet button()}
									<div class="rounded-md p-1.5 transition hover:bg-text/10">
										<DeleteIcon class="h-4 w-4 text-red-600" />
									</div>
								{/snippet}
								{#snippet slideout()}
									<div
										class="rounded-md bg-red-500/10 px-3 py-2 whitespace-nowrap text-red-600 dark:text-red-400"
									>
										{$LL.tags.deleteConfirm()}
									</div>
								{/snippet}
							</ConfirmButton>
						</div>
					</div>
				{/if}
			{/each}
		{/if}
	</div>
</div>
