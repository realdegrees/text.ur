<script lang="ts">
	import InfiniteTable from '$lib/components/infiniteScrollTable.svelte';
	import type { DocumentRead } from '$api/types';
	import DocumentIcon from '~icons/material-symbols/description-outline';
	import AddIcon from '~icons/material-symbols/add-2-rounded';
	import LL from '$i18n/i18n-svelte';
	import { api } from '$api/client';
	import type { Paginated } from '$api/pagination';
	import { validatePermissions } from '$api/validatePermissions';
	import { notification } from '$lib/stores/notificationStore';
	import { goto } from '$app/navigation';

	let { data } = $props();
	let documents = $derived(data.documents);
	let group = $derived(data.membership.group);

	function formatDate(dateString?: string): string {
		if (!dateString) return 'N/A';
		return new Date(dateString).toLocaleDateString();
	}

	function handleDocumentClick(document: DocumentRead): void {
		goto(`/dashboard/documents/${document.id}`);
	}
</script>

<div class="h-screen p-4">
	<div class="mb-4 flex w-full flex-row items-center justify-between gap-2">
		<h1 class="text-2xl font-bold">Documents</h1>
		{#if validatePermissions(data.membership, ['upload_documents'])}
			<a
				href="/dashboard/groups/{group.id}/documents/create"
				class="flex flex-row items-center gap-2 rounded bg-green-500/30 px-3 py-2.5 font-semibold shadow-inner shadow-black/30 transition hover:cursor-pointer hover:bg-green-500/40"
			>
				<AddIcon class="h-5 w-5" />
				Upload Document
			</a>
		{/if}
	</div>

	<InfiniteTable
		columns={[
			{
				label: 'Document Name',
				width: '3fr',
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
			}
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
</div>

{#snippet nameSnippet(document: DocumentRead)}
	<button
		onclick={() => handleDocumentClick(document)}
		class="text-text flex w-full flex-row items-center gap-2 text-left transition-colors hover:text-primary"
	>
		<DocumentIcon class="h-5 w-5" />
		<p class="font-semibold text-sm">{document.name}</p>
	</button>
{/snippet}

{#snippet visibilitySnippet(document: DocumentRead)}
	<span
		class="flex w-fit flex-row rounded-full px-2 py-1 text-xs font-semibold uppercase"
		class:bg-blue-100={document.visibility === 'public'}
		class:text-blue-800={document.visibility === 'public'}
		class:bg-yellow-100={document.visibility === 'restricted'}
		class:text-yellow-800={document.visibility === 'restricted'}
		class:bg-gray-100={document.visibility === 'private'}
		class:text-gray-800={document.visibility === 'private'}
	>
		{$LL.visibility[document.visibility].label()}
	</span>
{/snippet}

{#snippet dateSnippet(document: DocumentRead)}
	<div class="flex flex-col gap-0.5">
		<p class="text-sm">{formatDate(document.created_at)}</p>
		{#if document.updated_at && document.updated_at !== document.created_at}
			<p class="text-text/70 text-xs">Updated: {formatDate(document.updated_at)}</p>
		{/if}
	</div>
{/snippet}
