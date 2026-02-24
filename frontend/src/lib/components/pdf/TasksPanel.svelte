<script lang="ts">
	import TaskCard from './TaskCard.svelte';
	import LL from '$i18n/i18n-svelte';
	import { documentStore } from '$lib/runes/document.svelte';

	let completedCount = $derived(
		documentStore.tasks.reduce((count, task) => {
			const response = documentStore.taskResponses.get(task.id);
			const isCorrect = response?.is_correct ?? false;
			const isExhausted = (response?.attempts ?? 0) >= task.max_attempts && !isCorrect;
			return count + (isCorrect || isExhausted ? 1 : 0);
		}, 0)
	);

	let totalCount = $derived(documentStore.tasks.length);
</script>

<div class="flex h-full flex-col">
	<!-- Header with progress -->
	{#if totalCount > 0}
		<div class="flex items-center justify-between border-b border-text/10 px-3 py-2">
			<span class="text-xs font-semibold text-text/70">
				{$LL.tasks.completed({ count: completedCount, total: totalCount })}
			</span>
			<!-- Progress bar -->
			<div class="h-1.5 w-20 overflow-hidden rounded-full bg-text/10">
				<div
					class="h-full rounded-full bg-green-500 transition-all duration-300"
					style="width: {totalCount > 0 ? (completedCount / totalCount) * 100 : 0}%"
				></div>
			</div>
		</div>
	{/if}

	<!-- Task list (own scrolling, no PDF sync) -->
	<div class="custom-scrollbar flex-1 overflow-y-auto p-3">
		{#if totalCount === 0}
			<div class="flex h-full items-center justify-center p-4">
				<div class="text-center">
					<p class="text-sm text-text/40">{$LL.tasks.noTasks()}</p>
					<p class="mt-1 text-xs text-text/30">{$LL.tasks.noTasksDescription()}</p>
				</div>
			</div>
		{:else}
			<div class="flex flex-col gap-3">
				{#each documentStore.tasks as task, idx (task.id)}
					<TaskCard {task} index={idx} response={documentStore.taskResponses.get(task.id)} />
				{/each}
			</div>
		{/if}
	</div>
</div>
