<script lang="ts">
	import type { TaskRead, TaskResponseRead, TaskResponseCreate } from '$api/types';
	import LL from '$i18n/i18n-svelte';
	import ConfirmButton from '$lib/components/ConfirmButton.svelte';
	import { documentStore } from '$lib/runes/document.svelte';
	import { untrack } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import CheckIcon from '~icons/material-symbols/check-circle-outline';
	import CloseIcon from '~icons/material-symbols/cancel-outline';
	import InfoIcon from '~icons/material-symbols/info-outline';
	import ChevronDownIcon from '~icons/material-symbols/keyboard-arrow-down-rounded';
	import SendIcon from '~icons/material-symbols/send-outline';

	interface Props {
		task: TaskRead;
		index: number;
		response: TaskResponseRead | undefined;
	}

	let { task, index, response }: Props = $props();

	// Local answer state
	let selectedOptionIds = new SvelteSet<number>();
	let textAnswer = $state('');
	let numberAnswer = $state<number | undefined>(undefined);
	let isSubmitting = $state(false);
	let isCollapsed = $state(false);

	// Pre-fill local state from existing response (e.g., after tasks_updated reload).
	// Uses untrack for local state reads so user input doesn't trigger a reset loop.
	$effect(() => {
		if (response) {
			if (task.answer_type === 'multiple_choice' && response.answer?.selected_option_ids) {
				const incoming = new Set(response.answer.selected_option_ids as number[]);
				const current = untrack(() => new Set(selectedOptionIds));
				const same = incoming.size === current.size && [...incoming].every((id) => current.has(id));
				if (!same) {
					selectedOptionIds.clear();
					for (const id of incoming) {
						selectedOptionIds.add(id);
					}
				}
			}
			if (task.answer_type === 'string' && response.answer?.text != null) {
				const incoming = response.answer.text as string;
				if (untrack(() => textAnswer) !== incoming) {
					textAnswer = incoming;
				}
			}
			if (task.answer_type === 'number' && response.answer?.value != null) {
				const incoming = response.answer.value as number;
				if (untrack(() => numberAnswer) !== incoming) {
					numberAnswer = incoming;
				}
			}
		}
	});

	let isCorrect = $derived(response?.is_correct ?? false);
	let attempts = $derived(response?.attempts ?? 0);
	let maxAttempts = $derived(task.max_attempts);
	let attemptsRemaining = $derived(maxAttempts - attempts);
	let isExhausted = $derived(attempts >= maxAttempts && !isCorrect);
	let isLocked = $derived(isCorrect || isExhausted);
	let isLastTry = $derived(attemptsRemaining === 1 && !isLocked);

	// Auto-collapse when task becomes locked (correct or exhausted)
	$effect(() => {
		if (isLocked) {
			isCollapsed = true;
		}
	});

	// Check if answer is valid for submission
	let canSubmit = $derived.by(() => {
		if (isLocked || isSubmitting) return false;
		if (task.answer_type === 'multiple_choice') {
			return selectedOptionIds.size > 0;
		}
		if (task.answer_type === 'string') {
			return textAnswer.trim().length > 0;
		}
		if (task.answer_type === 'number') {
			return numberAnswer != null;
		}
		return false;
	});

	function toggleOption(optionId: number) {
		if (isLocked) return;
		if (selectedOptionIds.has(optionId)) {
			selectedOptionIds.delete(optionId);
		} else {
			selectedOptionIds.add(optionId);
		}
	}

	async function handleSubmit() {
		if (!canSubmit) return;
		isSubmitting = true;

		try {
			const payload: TaskResponseCreate = {};
			if (task.answer_type === 'multiple_choice') {
				payload.selected_option_ids = [...selectedOptionIds];
			} else if (task.answer_type === 'string') {
				payload.text = textAnswer;
			} else if (task.answer_type === 'number') {
				payload.value = numberAnswer ?? null;
			}

			await documentStore.submitTaskResponse(task.id, payload);
		} finally {
			isSubmitting = false;
		}
	}

	// Format the revealed correct answer
	function formatCorrectAnswer(answer: Record<string, unknown> | null | undefined): string {
		if (!answer) return '';
		if (answer.text != null) return String(answer.text);
		if (answer.value != null) return String(answer.value);
		if (answer.selected_option_ids) {
			const ids = answer.selected_option_ids as number[];
			return task.options
				.filter((o) => ids.includes(o.id))
				.map((o) => o.label)
				.join(', ');
		}
		return '';
	}
</script>

<div class="rounded-lg border border-text/15 bg-background p-3">
	<!-- Header: task number + points + status (always visible, clickable when locked) -->
	<button
		type="button"
		class="flex w-full items-center justify-between {isLocked
			? 'cursor-pointer'
			: 'cursor-default'}"
		onclick={() => {
			if (isLocked) isCollapsed = !isCollapsed;
		}}
		disabled={!isLocked}
	>
		<div class="flex items-center gap-2">
			<span class="text-xs font-bold text-text/50">#{index + 1}</span>
			<span class="rounded bg-primary/15 px-1.5 py-0.5 text-xs font-semibold text-primary">
				{task.points}
				{task.points === 1 ? 'pt' : 'pts'}
			</span>
		</div>
		<div class="flex items-center gap-1.5">
			{#if isCorrect}
				<div class="flex items-center gap-1 text-green-600">
					<CheckIcon class="h-4 w-4" />
					<span class="text-xs font-semibold">{$LL.tasks.correct()}</span>
				</div>
			{:else if isExhausted}
				<div class="flex items-center gap-1 text-red-500">
					<CloseIcon class="h-4 w-4" />
					<span class="text-xs font-semibold">{$LL.tasks.noTriesLeft()}</span>
				</div>
			{:else if attempts > 0}
				<div class="flex items-center gap-1 text-amber-500">
					<CloseIcon class="h-4 w-4" />
					<span class="text-xs">{$LL.tasks.incorrect()}</span>
				</div>
				<span class="rounded bg-text/10 px-1.5 py-0.5 text-xs text-text/60">
					{$LL.tasks.triesRemaining({ count: attemptsRemaining })}
				</span>
			{:else}
				<span class="rounded bg-text/10 px-1.5 py-0.5 text-xs text-text/60">
					{$LL.tasks.triesRemaining({ count: attemptsRemaining })}
				</span>
			{/if}
			{#if isLocked}
				<ChevronDownIcon
					class="h-4 w-4 text-text/40 transition-transform {isCollapsed ? '' : 'rotate-180'}"
				/>
			{/if}
		</div>
	</button>

	<!-- Collapsible body -->
	{#if !isCollapsed}
		<!-- Question -->
		<p class="mt-2 mb-3 text-sm font-medium">{task.question}</p>

		<!-- Answer input by type -->
		{#if task.answer_type === 'multiple_choice'}
			<div class="mb-3 flex flex-col gap-1.5">
				{#each task.options as option (option.id)}
					<label
						class="flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-sm transition-colors {isLocked
							? 'cursor-default opacity-70'
							: selectedOptionIds.has(option.id)
								? 'border-primary/50 bg-primary/10'
								: 'border-text/10 hover:bg-text/5'}"
					>
						<input
							type="checkbox"
							checked={selectedOptionIds.has(option.id)}
							onchange={() => toggleOption(option.id)}
							disabled={isLocked}
							class="cursor-pointer accent-primary"
						/>
						<span>{option.label}</span>
					</label>
				{/each}
			</div>
		{:else if task.answer_type === 'string'}
			<div class="mb-3">
				<input
					type="text"
					bind:value={textAnswer}
					disabled={isLocked}
					placeholder="Type your answer..."
					class="w-full rounded-md border border-text/20 bg-text/5 px-3 py-2 text-sm transition-colors outline-none focus:border-text/40 disabled:opacity-70"
				/>
				{#if task.string_match_mode === 'exact'}
					<div class="mt-1 flex items-center gap-1 text-xs text-text/40">
						<InfoIcon class="h-3 w-3" />
						<span>{$LL.tasks.exactMatchHint()}</span>
					</div>
				{:else}
					<div class="mt-1 flex items-center gap-1 text-xs text-text/40">
						<InfoIcon class="h-3 w-3" />
						<span>{$LL.tasks.caseInsensitiveHint()}</span>
					</div>
				{/if}
			</div>
		{:else if task.answer_type === 'number'}
			<div class="mb-3">
				<input
					type="number"
					step="any"
					bind:value={numberAnswer}
					disabled={isLocked}
					placeholder="Enter a number..."
					class="w-full rounded-md border border-text/20 bg-text/5 px-3 py-2 text-sm transition-colors outline-none focus:border-text/40 disabled:opacity-70"
				/>
			</div>
		{/if}

		<!-- Correct answer reveal (only when exhausted and wrong) -->
		{#if isExhausted && response?.correct_answer}
			<div class="mb-3 rounded-md border border-text/15 bg-text/5 px-3 py-2">
				<p class="text-xs font-semibold text-text/60">{$LL.tasks.correctAnswerWas()}</p>
				<p class="mt-0.5 text-sm text-text/80">{formatCorrectAnswer(response.correct_answer)}</p>
			</div>
		{/if}

		<!-- Submit button (only when not locked) -->
		{#if !isLocked}
			<ConfirmButton onConfirm={handleSubmit} disabled={!canSubmit || isSubmitting}>
				{#snippet button(isOpen)}
					<div
						class="flex items-center gap-2 rounded border-2 px-3 py-2 text-sm font-medium transition-colors {canSubmit &&
						!isSubmitting
							? isOpen
								? 'border-primary/80 bg-primary/20 text-primary'
								: 'border-primary/50 bg-primary/10 text-primary hover:bg-primary/20'
							: 'cursor-not-allowed border-text/10 bg-text/5 text-text/30'}"
					>
						<SendIcon class="h-4 w-4" />
						<p class="whitespace-nowrap">
							{isSubmitting ? '...' : $LL.tasks.submitAnswer()}
						</p>
					</div>
				{/snippet}

				{#snippet slideout()}
					<div
						class="px-3 py-2 whitespace-nowrap {isLastTry
							? 'bg-red-500/10 text-red-600 dark:text-red-400'
							: 'bg-primary/10 text-primary'}"
					>
						{isLastTry ? $LL.tasks.lastTry() : $LL.tasks.confirm()}
					</div>
				{/snippet}
			</ConfirmButton>
		{/if}
	{/if}
</div>
