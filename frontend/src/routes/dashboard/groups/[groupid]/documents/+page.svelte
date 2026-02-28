<script lang="ts">
	import type { DocumentRead } from '$api/types';
	import type { Paginated } from '$api/pagination';
	import LL from '$i18n/i18n-svelte';
	import AddIcon from '~icons/material-symbols/add-2-rounded';
	import { api } from '$api/client';
	import { sessionStore } from '$lib/runes/session.svelte';
	import { notification } from '$lib/stores/notificationStore';
	import { invalidate } from '$app/navigation';
	import DocumentCard from '$lib/components/DocumentCard.svelte';
	import { sortable } from '$lib/actions/sortable';
	import { infiniteScroll } from '$lib/util/infiniteScroll.svelte';

	let { data } = $props();
	let group = $derived(data.membership.group);
	let isAdmin = $derived(sessionStore.validatePermissions(['administrator']));

	const scroll = infiniteScroll<DocumentRead>(
		() => data.documents,
		async (offset, limit) => {
			const result = await api.get<Paginated<DocumentRead>>(
				`/documents?offset=${offset}&limit=${limit}`,
				{
					sort: [{ field: 'order', direction: 'asc' }],
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
		},
		25,
		true
	);

	async function handleReorder(fromIndex: number, toIndex: number) {
		const oldItems = [...scroll.items];

		// Optimistically reorder the local list immediately
		const newItems = [...oldItems];
		const [moved] = newItems.splice(fromIndex, 1);
		newItems.splice(toIndex, 0, moved);
		scroll.data = { ...scroll.data, data: newItems };

		// Persist to backend
		const ids = newItems.map((d) => d.id);
		const result = await api.update(`/groups/${group.id}/documents/reorder`, {
			document_ids: ids
		});

		if (!result.success) {
			// Revert on failure
			scroll.data = { ...scroll.data, data: oldItems };
			notification(result.error);
		} else {
			notification('success', $LL.documents.reorderSuccess());
			await invalidate('app:documents');
		}
	}
</script>

<div class="p-4">
	<div class="mb-4 flex w-full flex-row items-center justify-between gap-2">
		{#if isAdmin}
			<a
				href="/dashboard/groups/{group.id}/documents/create"
				class="flex btn-primary items-center gap-2 text-sm"
			>
				<AddIcon class="h-4 w-4" />
				{$LL.documents.uploadDocument()}
			</a>
		{/if}
	</div>

	{#if scroll.items.length === 0 && !scroll.hasMore}
		<p class="py-8 text-center text-text/50">{$LL.documents.noDocuments()}</p>
	{:else}
		<div
			bind:this={scroll.scrollContainer.node}
			class="h-full custom-scrollbar flex-1 overflow-y-auto"
		>
			<div
				class="flex flex-col gap-2"
				use:sortable={{ onReorder: handleReorder, enabled: isAdmin && scroll.items.length > 1 }}
			>
				{#each scroll.items as document (document.id)}
					<DocumentCard {document} groupId={group.id} {isAdmin} />
				{/each}
			</div>

			<!-- Infinite scroll sentinel -->
			<div bind:this={scroll.sentinel.node} class="h-4 w-full"></div>
		</div>
	{/if}
</div>
