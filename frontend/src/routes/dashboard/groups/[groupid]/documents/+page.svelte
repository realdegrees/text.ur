<script lang="ts">
	import InfiniteTable from '$lib/components/infiniteScrollTable.svelte';
	import type { DocumentRead } from '$api/types';
	import DocumentIcon from '~icons/material-symbols/description-outline';
	import AddIcon from '~icons/material-symbols/add-2-rounded';
	import EditIcon from '~icons/material-symbols/edit-outline';
	import { api } from '$api/client';
	import type { Paginated } from '$api/pagination';
	import { sessionStore } from '$lib/runes/session.svelte.js';
	import { notification } from '$lib/stores/notificationStore';
	import { goto, invalidateAll } from '$app/navigation';
	import { formatDateTime } from '$lib/util/dateFormat';
	import ConfirmButton from '$lib/components/ConfirmButton.svelte';
	import DocumentVisibility from '$lib/components/DocumentVisibility.svelte';
	import DeleteIcon from '~icons/material-symbols/delete-outline';

	let { data } = $props();
	let documents = $derived(data.documents);
	let group = $derived(data.membership.group);

	function handleDocumentClick(document: DocumentRead): void {
		goto(`/documents/${document.id}`);
	}
</script>

<div class="p-4">
	<div class="mb-4 flex w-full flex-row items-center justify-between gap-2">
		{#if sessionStore.validatePermissions(['upload_documents'])}
			<a
				href="/dashboard/groups/{group.id}/documents/create"
				class="flex flex-row items-center gap-2 rounded bg-green-500/30 px-3 py-2.5 font-semibold shadow-inner shadow-black/30 transition hover:cursor-pointer hover:bg-green-500/40"
			>
				<AddIcon class="h-5 w-5" />
				Upload Document
			</a>
		{/if}
	</div>

	{#key documents}
		<InfiniteTable
			columns={[
				{
					label: 'Document Name',
					width: '1fr',
					snippet: nameSnippet
				},
				{
					label: 'Visibility',
					width: '1fr',
					snippet: visibilitySnippet
				},
				{
					label: 'Created',
					width: '1fr',
					snippet: dateSnippet
				},
				...(sessionStore.validatePermissions(['delete_documents']) ||
				sessionStore.validatePermissions(['upload_documents'])
					? [
							{
								label: 'Actions',
								width: 'auto',
								snippet: actionsSnippet
							}
						]
					: [])
			]}
			data={documents}
			loadMore={async (offset, limit) => {
				const result = await api.get<Paginated<DocumentRead>>(
					`/documents?offset=${offset}&limit=${limit}`,
					{
						sort: [{ field: 'created_at', direction: 'desc' }],
						filters: [
							{
								field: 'group_id',
								operator: '==',
								value: group?.id
							}
						]
					}
				);
				if (!result.success) {
					notification(result.error);
					return undefined;
				}
				return result.data;
			}}
			step={20}
			rowBgClass="bg-inset/90"
		/>
	{/key}
</div>

{#snippet nameSnippet(document: DocumentRead)}
	<button
		onclick={() => handleDocumentClick(document)}
		class="flex w-full flex-row items-center gap-2 text-left text-text transition-colors hover:text-primary"
	>
		<DocumentIcon class="h-5 w-5" />
		<p class="text-sm font-semibold">{document.name}</p>
	</button>
{/snippet}

{#snippet visibilitySnippet(document: DocumentRead)}
	<div class="flex w-full items-center justify-start">
		<DocumentVisibility {document} canEdit={false} />
	</div>
{/snippet}

{#snippet dateSnippet(document: DocumentRead)}
	<div class="flex flex-col gap-0.5">
		<p class="text-sm">{formatDateTime(document.created_at)}</p>
		{#if document.updated_at && document.updated_at !== document.created_at}
			<p class="text-xs text-text/70">Updated: {formatDateTime(document.updated_at)}</p>
		{/if}
	</div>
{/snippet}

{#snippet actionsSnippet(document: DocumentRead)}
	<div class="flex w-full flex-row items-center justify-end gap-2">
		{#if sessionStore.validatePermissions(['upload_documents'])}
			<button
				onclick={() => goto(`/dashboard/groups/${group.id}/documents/${document.id}/settings`)}
				class="transition hover:text-primary"
				aria-label="Edit document settings"
			>
				<EditIcon class="h-5 w-5" />
			</button>
		{/if}
		{#if sessionStore.validatePermissions(['delete_documents'])}
			<ConfirmButton
				onConfirm={async () => {
					const result = await api.delete(`/documents/${document.id}`);
					if (!result.success) {
						notification(result.error);
						return;
					}
					notification('success', 'Document deleted successfully');
					invalidateAll();
				}}
			>
				{#snippet button()}
					<DeleteIcon class="h-5 w-5 text-red-600 hover:text-red-800" />
				{/snippet}
				{#snippet slideout()}
					<div class="bg-red-500/10 px-3 py-2 whitespace-nowrap text-red-600 dark:text-red-400">
						Delete?
					</div>
				{/snippet}
			</ConfirmButton>
		{/if}
	</div>
{/snippet}
