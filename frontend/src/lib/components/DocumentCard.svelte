<script lang="ts">
	import type { DocumentRead } from '$api/types';
	import { api } from '$api/client';
	import { goto, invalidate } from '$app/navigation';
	import { notification } from '$lib/stores/notificationStore';
	import { formatDateTime } from '$lib/util/dateFormat';
	import LL from '$i18n/i18n-svelte';
	import ConfirmButton from '$lib/components/ConfirmButton.svelte';
	import DocumentIcon from '~icons/material-symbols/description-outline';
	import EditIcon from '~icons/material-symbols/edit-outline';
	import DeleteIcon from '~icons/material-symbols/delete-outline';
	import DragIcon from '~icons/material-symbols/drag-indicator';
	import CommentIcon from '~icons/material-symbols/comment-outline';
	import TaskIcon from '~icons/material-symbols/task-outline';
	import LockIcon from '~icons/material-symbols/lock';
	import PublicIcon from '~icons/material-symbols/public';

	interface Props {
		document: DocumentRead;
		groupId: string;
		isAdmin: boolean;
	}

	let { document, groupId, isAdmin }: Props = $props();

	const taskTotal = $derived(document.task_count);
	const taskCompleted = $derived(document.user_completed_task_count ?? 0);
	const taskProgressPct = $derived(
		taskTotal > 0 ? Math.round((taskCompleted / taskTotal) * 100) : 0
	);
</script>

<div
	data-sortable-id={document.id}
	class="flex items-stretch gap-0 rounded-lg border border-text/15 bg-inset/90 shadow-sm transition hover:border-text/25"
>
	<!-- Drag handle (admin only) -->
	{#if isAdmin}
		<div
			data-drag-handle
			class="flex cursor-grab items-center px-2 text-text/30 hover:text-text/60"
		>
			<DragIcon class="h-5 w-5" />
		</div>
	{/if}

	<!-- Main card content -->
	<button
		onclick={() => goto(`/documents/${document.id}`)}
		class="flex min-w-0 flex-1 cursor-pointer flex-col gap-2 p-3 text-left transition-colors hover:bg-text/5"
	>
		<!-- Row 1: Name + visibility -->
		<div class="flex items-center gap-2">
			<DocumentIcon class="h-5 w-5 shrink-0 text-text/60" />
			<h3 class="min-w-0 flex-1 truncate text-base font-semibold text-text">
				{document.name}
			</h3>
		</div>

		<!-- Row 2: Description (if present) -->
		{#if document.description}
			<p class="line-clamp-2 text-xs text-text/60">
				{document.description}
			</p>
		{/if}

		<!-- Row 3: Stats and badges -->
		<div class="flex flex-wrap items-center gap-2">
			<!-- Visibility badge -->
			{#if document.visibility === 'private'}
				<span
					class="flex items-center gap-1 rounded-full bg-yellow-300 px-2 py-0.5 text-xs font-semibold text-black/90 uppercase"
				>
					<LockIcon class="h-3 w-3" />
					{$LL.visibility.private.label()}
				</span>
			{:else}
				<span
					class="flex items-center gap-1 rounded-full bg-green-300 px-2 py-0.5 text-xs font-semibold text-black/90 uppercase"
				>
					<PublicIcon class="h-3 w-3" />
					{$LL.visibility.public.label()}
				</span>
			{/if}

			<!-- View mode badge -->
			<span class="rounded bg-text/10 px-2 py-0.5 text-xs text-text/70">
				{$LL.pdf.viewMode.label()}: {document.view_mode === 'restricted'
					? $LL.pdf.viewMode.restricted()
					: $LL.pdf.viewMode.public()}
			</span>

			<!-- Comment count -->
			{#if document.root_comment_count > 0}
				<span class="flex items-center gap-1 text-xs text-text/60">
					<CommentIcon class="h-3.5 w-3.5" />
					{document.root_comment_count}
				</span>
			{/if}

			<!-- Tags -->
			{#each document.tags as tag (tag.id)}
				<span
					class="rounded-full px-2 py-0.5 text-xs font-medium text-white"
					style="background-color: {tag.color}"
				>
					{tag.label}
				</span>
			{/each}
		</div>

		<!-- Row 4: Task progress (if tasks exist) -->
		{#if taskTotal > 0}
			<div class="flex items-center gap-2">
				<TaskIcon class="h-3.5 w-3.5 shrink-0 text-text/50" />
				<div class="h-1.5 flex-1 rounded-full bg-text/10">
					<div
						class="h-full rounded-full bg-green-500 transition-all"
						style="width: {taskProgressPct}%"
					></div>
				</div>
				<span class="shrink-0 text-xs text-text/60">
					{$LL.tasks.completed({ count: taskCompleted, total: taskTotal })}
				</span>
			</div>
		{/if}

		<!-- Row 5: Dates -->
		<div class="flex items-center gap-3 text-xs text-text/50">
			<span>{$LL.documents.created()}: {formatDateTime(document.created_at)}</span>
			{#if document.updated_at && document.updated_at !== document.created_at}
				<span>{$LL.documents.updated({ date: formatDateTime(document.updated_at) })}</span>
			{/if}
		</div>
	</button>

	<!-- Admin actions -->
	{#if isAdmin}
		<div class="flex flex-col items-center justify-around border-l border-text/10 px-3">
			<button
				onclick={(e) => {
					e.stopPropagation();
					goto(`/dashboard/groups/${groupId}/documents/${document.id}/settings`);
				}}
				class="cursor-pointer text-text/60 transition hover:text-primary"
				aria-label={$LL.documents.editSettings()}
			>
				<EditIcon class="h-5 w-5" />
			</button>
			<ConfirmButton
				onConfirm={async () => {
					const result = await api.delete(`/documents/${document.id}`);
					if (!result.success) {
						notification(result.error);
						return;
					}
					notification('success', $LL.documents.deleteSuccess());
					invalidate('app:documents');
				}}
			>
				{#snippet button()}
					<DeleteIcon class="h-5 w-5 cursor-pointer text-text/60 hover:text-red-400/80" />
				{/snippet}
				{#snippet slideout()}
					<div class="px-1 py-2 whitespace-nowrap text-red-600 dark:text-red-400">
						{$LL.documents.deleteConfirm()}
					</div>
				{/snippet}
			</ConfirmButton>
		</div>
	{/if}
</div>
