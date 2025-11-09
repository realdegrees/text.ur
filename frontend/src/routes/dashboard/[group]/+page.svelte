<script lang="ts">
	import type { GroupRead, DocumentRead } from '$api/types';
	import LL from '$i18n/i18n-svelte';
	import PaginatedList from '$lib/components/paginatedList.svelte';
	import SettingsIcon from '~icons/material-symbols/settings-outline';
	import PeopleIcon from '~icons/material-symbols/group-outline';
	import DocumentIcon from '~icons/material-symbols/description-outline';

	let { data } = $props();
	let group: GroupRead = $derived(data.group!);
	let documents = $derived(data.documents);

	function formatDate(dateString?: string): string {
		if (!dateString) return 'N/A';
		return new Date(dateString).toLocaleDateString();
	}
</script>

<div class="flex h-full w-full flex-col gap-4">
	<!-- Header Section -->
	<div class="flex flex-row items-start justify-between">
		<div class="flex flex-col gap-2">
			<h1 class="text-3xl font-bold">{group.name}</h1>
			<div class="flex flex-col gap-1 text-sm text-text/70">
				<span
					>{$LL.groupOwnerLabel()}:
					<span class="font-semibold">{group.owner?.username || 'Unknown'}</span></span
				>
				<span>Created: {formatDate(group.created_at)}</span>
				{#if group.updated_at && group.updated_at !== group.created_at}
					<span>Last updated: {formatDate(group.updated_at)}</span>
				{/if}
			</div>
		</div>

		<!-- Action Buttons -->
		<div class="flex flex-row gap-2">
			<a
				href="/dashboard/{group.id}/memberships"
				class="flex flex-row items-center gap-2 rounded-md bg-text/10 px-4 py-2 transition-all hover:bg-text/20"
			>
				<PeopleIcon class="h-5 w-5" />
				<span>Members ({group.member_count})</span>
			</a>
			<a
				href="/dashboard/{group.id}/settings"
				class="flex flex-row items-center gap-2 rounded-md bg-text/10 px-4 py-2 transition-all hover:bg-text/20"
			>
				<SettingsIcon class="h-5 w-5" />
				<span>Settings</span>
			</a>
		</div>
	</div>

	<hr class="border-text/20" />

	<!-- Group Information Section -->
	<div class="flex flex-col gap-2">
		<h2 class="text-xl font-semibold">Group Information</h2>
		<div class="grid grid-cols-2 gap-4 rounded-md bg-text/5 p-4">
			<div class="flex flex-col gap-1">
				<span class="text-sm font-semibold text-text/70">Group ID</span>
				<span class="font-mono text-sm">{group.id}</span>
			</div>
			<div class="flex flex-col gap-1">
				<span class="text-sm font-semibold text-text/70">Member Count</span>
				<span>{group.member_count}</span>
			</div>
			<div class="flex flex-col gap-1">
				<span class="text-sm font-semibold text-text/70">Owner</span>
				<span>{group.owner?.username || 'Unknown'}</span>
			</div>
			<div class="flex flex-col gap-1">
				<span class="text-sm font-semibold text-text/70">Created At</span>
				<span>{formatDate(group.created_at)}</span>
			</div>
		</div>
	</div>

	<hr class="border-text/20" />

	<!-- Documents Section -->
	<div class="flex flex-col gap-2">
		<div class="flex flex-row items-center gap-2">
			<DocumentIcon class="h-6 w-6" />
			<h2 class="text-xl font-semibold">Documents</h2>
		</div>

		{#if documents.total === 0}
			<div class="flex flex-col items-center justify-center gap-2 rounded-md bg-text/5 p-8">
				<DocumentIcon class="h-12 w-12 text-text/30" />
				<p class="text-text/70">No documents in this group yet</p>
			</div>
		{:else}
			<PaginatedList data={documents}>
				{#snippet itemSnippet(document: DocumentRead)}
					<div
						class="flex flex-row items-center justify-between rounded-md bg-text/5 p-3 transition-all hover:bg-text/10"
					>
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
