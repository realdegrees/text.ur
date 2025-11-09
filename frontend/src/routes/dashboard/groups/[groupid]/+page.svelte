<script lang="ts">
	import type { DocumentRead } from "$api/types";
	import LL from "$i18n/i18n-svelte";
	import PaginatedList from "$lib/components/paginatedList.svelte";
	import DocumentIcon from "~icons/material-symbols/description-outline";

	let { data } = $props();
	let documents = $derived(data.documents);

	function formatDate(dateString?: string): string {
		if (!dateString) return "N/A";
		return new Date(dateString).toLocaleDateString();
	}
</script>

<div class="flex h-full w-full flex-col gap-4">
	<!-- Documents Section -->
	<div class="flex flex-col gap-2">
		{#if documents.total === 0}
			<div class="flex flex-col items-center justify-center gap-2 rounded-md bg-text/5 p-8">
				<DocumentIcon class="h-12 w-12 text-text/30" />
				<p class="text-text/70">No documents in this group yet</p>
			</div>
		{:else}
			<PaginatedList data={documents}>
				{#snippet itemSnippet(document: DocumentRead)}
					<div class="flex flex-row items-center justify-between rounded-md bg-text/5 p-3 transition-all hover:bg-text/10">
						<div class="flex flex-row items-center gap-3">
							<DocumentIcon class="h-5 w-5" />
							<div class="flex flex-col gap-0.5">
								<span class="font-semibold">{document.id}</span>
								<span class="text-xs text-text/70">Visibility: {document.visibility}</span>
							</div>
						</div>
						<div class="flex flex-col items-end gap-0.5 text-xs text-text/70">
							<span>Created: {formatDate(document.created_at)}</span>
							{#if document.updated_at && document.updated_at !== document.created_at}
								<span>Updated: {formatDate(document.updated_at)}</span>
							{/if}
						</div>
					</div>
				{/snippet}
			</PaginatedList>
		{/if}
	</div>
</div>
