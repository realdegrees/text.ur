<script lang="ts">
	import InfiniteTable from '$lib/components/infiniteScrollTable.svelte';
	import type { DocumentRead } from '$api/types';
	import LL from '$i18n/i18n-svelte';
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
		{#if sessionStore.validatePermissions(['administrator'])}
			<a
				href="/dashboard/groups/{group.id}/documents/create"
				class="flex flex-row items-center gap-2 rounded bg-green-500/30 px-3 py-2.5 font-semibold shadow-inner shadow-black/30 transition hover:cursor-pointer hover:bg-green-500/40"
			>
				<AddIcon class="h-5 w-5" />
				{$LL.documents.uploadDocument()}
			</a>
		{/if}
	</div>

	{#key documents}
		<InfiniteTable
			columns={[
				{
					label: $LL.documents.documentName(),
					width: '1fr',
					snippet: nameSnippet
				},
				...(sessionStore.validatePermissions(['administrator'])
					? [
							{
								label: $LL.visibility.label(),
								width: '1fr',
								snippet: visibilitySnippet
							}
						]
					: []),
				{
					label: $LL.documents.created(),
					width: '1fr',
					snippet: dateSnippet
				},
				...(sessionStore.validatePermissions(['administrator'])
					? [
							{
								label: $LL.actions(),
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
		<DocumentVisibility {document} canEdit={sessionStore.validatePermissions(['administrator'])} />
	</div>
{/snippet}

{#snippet dateSnippet(document: DocumentRead)}
	<div class="flex flex-col gap-0.5">
		<p class="text-sm text-text/90">{formatDateTime(document.created_at)}</p>
		{#if document.updated_at && document.updated_at !== document.created_at}
			<p class="text-xs text-text/60">{$LL.documents.updated({ date: formatDateTime(document.updated_at) })}</p>
		{/if}
	</div>
{/snippet}

{#snippet actionsSnippet(document: DocumentRead)}
	<div class="flex w-full flex-row items-center justify-end gap-2">
		{#if sessionStore.validatePermissions(['administrator'])}
			<button
				onclick={() => goto(`/dashboard/groups/${group.id}/documents/${document.id}/settings`)}
				class="cursor-pointer text-text/80 transition hover:text-primary"
				aria-label={$LL.documents.editSettings()}
			>
				<EditIcon class="h-5 w-5" />
			</button>
		{/if}
		{#if sessionStore.validatePermissions(['administrator'])}
			<ConfirmButton
				onConfirm={async () => {
					const result = await api.delete(`/documents/${document.id}`);
					if (!result.success) {
						notification(result.error);
						return;
					}
					notification('success', $LL.documents.deleteSuccess());
					invalidateAll();
				}}
			>
				{#snippet button()}
					<DeleteIcon class="h-5 w-5 cursor-pointer text-text/80 hover:text-red-400/80" />
				{/snippet}
				{#snippet slideout()}
					<div class="px-1 py-2 whitespace-nowrap text-red-600 dark:text-red-400">{$LL.documents.deleteConfirm()}</div>
				{/snippet}
			</ConfirmButton>
		{/if}
	</div>
{/snippet}
