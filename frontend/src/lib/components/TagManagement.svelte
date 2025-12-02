<script lang="ts">
	import { api } from '$api/client';
	import type { DocumentRead, TagRead } from '$api/types';
	import { notification } from '$lib/stores/notificationStore';
	import { invalidateAll } from '$app/navigation';
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

	// New tag form state
	let newTag = $state({
		label: '',
		description: '',
		color: '#3B82F6' // Default blue color
	});

	// Edit tag form state
	let editTag = $state<{ label: string; description: string; color: string }>({
		label: '',
		description: '',
		color: ''
	});

	async function createTag() {
		if (!newTag.label.trim()) {
			notification('error', 'Tag label is required');
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

		notification('success', 'Tag created successfully');
		resetNewTagForm();
		await invalidateAll();
	}

	async function updateTag(tagId: number) {
		if (!editTag.label.trim()) {
			notification('error', 'Tag label is required');
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

		notification('success', 'Tag updated successfully');
		editingTagId = null;
		await invalidateAll();
	}

	async function deleteTag(tagId: number) {
		const result = await api.delete(`/documents/${document.id}/tags/${tagId}`);

		if (!result.success) {
			notification(result.error);
			return;
		}

		notification('success', 'Tag deleted successfully');
		await invalidateAll();
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
	}

	function resetNewTagForm() {
		isAddingTag = false;
		newTag = {
			label: '',
			description: '',
			color: '#3B82F6'
		};
	}
</script>

<div class="flex flex-col gap-4">
	<div class="flex items-center justify-between">
		<div class="text-sm font-semibold text-text/70">Tags</div>
		<button
			onclick={() => (isAddingTag = !isAddingTag)}
			class="flex items-center gap-2 rounded-md bg-primary/20 px-3 py-2 text-sm font-semibold transition hover:bg-primary/30"
		>
			<AddIcon class="h-4 w-4" />
			Add Tag
		</button>
	</div>

	<!-- Add Tag Form -->
	{#if isAddingTag}
		<div class="flex flex-col gap-3 rounded-md border border-text/20 bg-text/5 p-4">
			<div class="text-sm font-semibold">New Tag</div>
			<div class="grid grid-cols-1 gap-3 md:grid-cols-2">
				<div class="flex flex-col gap-1.5">
					<label for="new-tag-label" class="text-xs font-semibold text-text/70">Label *</label>
					<input
						id="new-tag-label"
						type="text"
						bind:value={newTag.label}
						placeholder="Tag label"
						maxlength="50"
						class="rounded-md border border-text/20 bg-text/5 px-3 py-2 text-sm outline-none transition-colors focus:border-text/50"
					/>
				</div>
				<div class="flex flex-col gap-1.5">
					<label for="new-tag-color" class="text-xs font-semibold text-text/70">Color *</label>
					<div class="flex items-center gap-2">
						<input
							id="new-tag-color"
							type="color"
							bind:value={newTag.color}
							class="h-10 w-16 cursor-pointer rounded-md border border-text/20"
						/>
						<input
							type="text"
							bind:value={newTag.color}
							pattern={"^#[0-9A-Fa-f]{6}$"}
							placeholder="#3B82F6"
							maxlength="7"
							class="flex-1 rounded-md border border-text/20 bg-text/5 px-3 py-2 text-sm font-mono uppercase outline-none transition-colors focus:border-text/50"
						/>
					</div>
				</div>
				<div class="flex flex-col gap-1.5 md:col-span-2">
					<label for="new-tag-description" class="text-xs font-semibold text-text/70"
						>Description</label
					>
					<textarea
						id="new-tag-description"
						bind:value={newTag.description}
						placeholder="Optional description for this tag"
						maxlength="200"
						rows="2"
						class="rounded-md border border-text/20 bg-text/5 px-3 py-2 text-sm outline-none transition-colors focus:border-text/50"
					></textarea>
				</div>
			</div>
			<div class="flex items-center gap-2">
				<button
					onclick={createTag}
					class="flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-semibold transition hover:bg-primary/80"
				>
					<SaveIcon class="h-4 w-4" />
					Create Tag
				</button>
				<button
					onclick={resetNewTagForm}
					class="flex items-center gap-2 rounded-md bg-text/10 px-3 py-2 text-sm font-semibold transition hover:bg-text/20"
				>
					<CancelIcon class="h-4 w-4" />
					Cancel
				</button>
			</div>
		</div>
	{/if}

	<!-- Tags List -->
	<div class="flex flex-col gap-2">
		{#if tags.length === 0}
			<p class="text-sm text-text/50">No tags created yet</p>
		{:else}
			{#each tags as tag (tag.id)}
				{#if editingTagId === tag.id}
					<!-- Edit Form -->
					<div class="flex flex-col gap-3 rounded-md border border-text/20 bg-text/5 p-4">
						<div class="text-sm font-semibold">Edit Tag</div>
						<div class="grid grid-cols-1 gap-3 md:grid-cols-2">
							<div class="flex flex-col gap-1.5">
								<label for="edit-tag-label-{tag.id}" class="text-xs font-semibold text-text/70"
									>Label *</label
								>
								<input
									id="edit-tag-label-{tag.id}"
									type="text"
									bind:value={editTag.label}
									placeholder="e.g., Bug, Question"
									maxlength="50"
									class="rounded-md border border-text/20 bg-text/5 px-3 py-2 text-sm outline-none transition-colors focus:border-text/50"
								/>
							</div>
							<div class="flex flex-col gap-1.5">
								<label for="edit-tag-color-{tag.id}" class="text-xs font-semibold text-text/70"
									>Color *</label
								>
								<div class="flex items-center gap-2">
									<input
										id="edit-tag-color-{tag.id}"
										type="color"
										bind:value={editTag.color}
										class="h-10 w-16 cursor-pointer rounded-md border border-text/20"
									/>
									<input
										type="text"
										bind:value={editTag.color}
										pattern={"^#[0-9A-Fa-f]{6}$"}
										placeholder="#3B82F6"
										maxlength="7"
										class="flex-1 rounded-md border border-text/20 bg-text/5 px-3 py-2 text-sm font-mono uppercase outline-none transition-colors focus:border-text/50"
									/>
								</div>
							</div>
							<div class="flex flex-col gap-1.5 md:col-span-2">
								<label for="edit-tag-description-{tag.id}" class="text-xs font-semibold text-text/70"
									>Description</label
								>
								<textarea
									id="edit-tag-description-{tag.id}"
									bind:value={editTag.description}
									placeholder="Optional description for this tag"
									maxlength="200"
									rows="2"
									class="rounded-md border border-text/20 bg-text/5 px-3 py-2 text-sm outline-none transition-colors focus:border-text/50"
								></textarea>
							</div>
						</div>
						<div class="flex items-center gap-2">
							<button
								onclick={() => updateTag(tag.id)}
								class="flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-semibold transition hover:bg-primary/80"
							>
								<SaveIcon class="h-4 w-4" />
								Save Changes
							</button>
							<button
								onclick={cancelEdit}
								class="flex items-center gap-2 rounded-md bg-text/10 px-3 py-2 text-sm font-semibold transition hover:bg-text/20"
							>
								<CancelIcon class="h-4 w-4" />
								Cancel
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
								aria-label="Edit tag"
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
										class="whitespace-nowrap rounded-md bg-red-500/10 px-3 py-2 text-red-600 dark:text-red-400"
									>
										Delete?
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
