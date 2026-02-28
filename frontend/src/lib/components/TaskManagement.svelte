<script lang="ts">
	import { api } from '$api/client';
	import type { DocumentRead, TaskAdminRead, TaskOptionCreate, AnswerType } from '$api/types';
	import { notification } from '$lib/stores/notificationStore';
	import { invalidate } from '$app/navigation';
	import LL from '$i18n/i18n-svelte';
	import AddIcon from '~icons/material-symbols/add-2-rounded';
	import EditIcon from '~icons/material-symbols/edit-outline';
	import DeleteIcon from '~icons/material-symbols/delete-outline';
	import SaveIcon from '~icons/material-symbols/save-outline';
	import CancelIcon from '~icons/material-symbols/cancel-outline';
	import DragIcon from '~icons/material-symbols/drag-indicator';
	import ConfirmButton from '$lib/components/ConfirmButton.svelte';
	import Select from '$lib/components/Select.svelte';
	import { sortable } from '$lib/actions/sortable';

	interface Props {
		document: DocumentRead;
	}

	let { document }: Props = $props();

	let tasks = $state<TaskAdminRead[]>([]);
	let isAddingTask = $state(false);
	let editingTaskId = $state<number | null>(null);
	let isLoading = $state(true);

	// New task form state
	let newTask = $state(createEmptyTask());

	// Edit task form state
	let editTask = $state(createEmptyTask());
	let editCustomAttempts = $state(false);

	// Custom attempts toggle for new task
	let newCustomAttempts = $state(false);

	function createEmptyTask() {
		return {
			question: '',
			answer_type: 'multiple_choice' as AnswerType,
			correct_string_answer: '',
			correct_number_answer: null as number | null,
			number_tolerance: null as number | null,
			string_match_mode: 'case_insensitive' as 'exact' | 'case_insensitive',
			points: 1,
			order: 0,
			max_attempts: document.default_max_attempts,
			options: [
				{ label: '', is_correct: false, order: 0 },
				{ label: '', is_correct: false, order: 1 }
			] as TaskOptionCreate[]
		};
	}

	// Fetch tasks on mount
	$effect(() => {
		loadTasks();
	});

	async function loadTasks() {
		isLoading = true;
		const result = await api.get<TaskAdminRead[]>(`/documents/${document.id}/tasks`);
		if (result.success) {
			tasks = result.data;
		} else {
			notification(result.error);
		}
		isLoading = false;
	}

	async function createTask() {
		if (!newTask.question.trim()) {
			notification('error', $LL.tasks.questionRequired());
			return;
		}

		const payload: Record<string, unknown> = {
			question: newTask.question.trim(),
			answer_type: newTask.answer_type,
			points: newTask.points,
			order: tasks.length,
			max_attempts: newCustomAttempts ? newTask.max_attempts : document.default_max_attempts,
			string_match_mode: newTask.string_match_mode
		};

		if (newTask.answer_type === 'multiple_choice') {
			payload.options = newTask.options.map((o, i) => ({
				label: o.label,
				is_correct: o.is_correct,
				order: i
			}));
		} else if (newTask.answer_type === 'string') {
			payload.correct_string_answer = newTask.correct_string_answer;
		} else if (newTask.answer_type === 'number') {
			payload.correct_number_answer = newTask.correct_number_answer;
			if (newTask.number_tolerance !== null && newTask.number_tolerance >= 0) {
				payload.number_tolerance = newTask.number_tolerance;
			}
		}

		const result = await api.post<TaskAdminRead>(`/documents/${document.id}/tasks`, payload);

		if (!result.success) {
			notification(result.error);
			return;
		}

		notification('success', $LL.tasks.createSuccess());
		resetNewTaskForm();
		await loadTasks();
		await invalidate('app:document');
	}

	async function updateTask(taskId: number) {
		if (!editTask.question.trim()) {
			notification('error', $LL.tasks.questionRequired());
			return;
		}

		const payload: Record<string, unknown> = {
			question: editTask.question.trim(),
			answer_type: editTask.answer_type,
			points: editTask.points,
			max_attempts: editCustomAttempts ? editTask.max_attempts : document.default_max_attempts,
			string_match_mode: editTask.string_match_mode
		};

		if (editTask.answer_type === 'multiple_choice') {
			payload.options = editTask.options.map((o, i) => ({
				label: o.label,
				is_correct: o.is_correct,
				order: i
			}));
		} else if (editTask.answer_type === 'string') {
			payload.correct_string_answer = editTask.correct_string_answer;
		} else if (editTask.answer_type === 'number') {
			payload.correct_number_answer = editTask.correct_number_answer;
			if (editTask.number_tolerance !== null && editTask.number_tolerance >= 0) {
				payload.number_tolerance = editTask.number_tolerance;
			}
		}

		const result = await api.update(`/documents/${document.id}/tasks/${taskId}`, payload);

		if (!result.success) {
			notification(result.error);
			return;
		}

		notification('success', $LL.tasks.updateSuccess());
		editingTaskId = null;
		await loadTasks();
		await invalidate('app:document');
	}

	async function deleteTask(taskId: number) {
		const result = await api.delete(`/documents/${document.id}/tasks/${taskId}`);

		if (!result.success) {
			notification(result.error);
			return;
		}

		notification('success', $LL.tasks.deleteSuccess());
		await loadTasks();
		await invalidate('app:document');
	}

	async function handleReorder(fromIndex: number, toIndex: number) {
		const oldTasks = [...tasks];

		// Optimistically reorder locally
		const newTasks = [...oldTasks];
		const [moved] = newTasks.splice(fromIndex, 1);
		newTasks.splice(toIndex, 0, moved);
		tasks = newTasks;

		// Persist to backend
		const ids = newTasks.map((t) => t.id);
		const result = await api.update(`/documents/${document.id}/tasks/reorder`, {
			task_ids: ids
		});

		if (!result.success) {
			tasks = oldTasks;
			notification(result.error);
		}
	}

	function startEditingTask(task: TaskAdminRead) {
		editingTaskId = task.id;
		const isCustom = task.max_attempts !== document.default_max_attempts;
		editCustomAttempts = isCustom;
		editTask = {
			question: task.question,
			answer_type: task.answer_type as AnswerType,
			correct_string_answer: task.correct_string_answer || '',
			correct_number_answer: task.correct_number_answer,
			number_tolerance: task.number_tolerance,
			string_match_mode: task.string_match_mode as 'exact' | 'case_insensitive',
			points: task.points,
			order: task.order,
			max_attempts: task.max_attempts,
			options: task.options.map((o) => ({
				label: o.label,
				is_correct: o.is_correct,
				order: o.order
			}))
		};
	}

	function cancelEdit() {
		editingTaskId = null;
		editCustomAttempts = false;
	}

	function resetNewTaskForm() {
		isAddingTask = false;
		newCustomAttempts = false;
		newTask = createEmptyTask();
	}

	function addOption(opts: TaskOptionCreate[]) {
		opts.push({ label: '', is_correct: false, order: opts.length });
	}

	function removeOption(opts: TaskOptionCreate[], index: number) {
		opts.splice(index, 1);
	}

	function answerTypeLabel(type: AnswerType): string {
		switch (type) {
			case 'multiple_choice':
				return $LL.tasks.multipleChoice();
			case 'string':
				return $LL.tasks.textAnswer();
			case 'number':
				return $LL.tasks.numberAnswer();
			default:
				return type;
		}
	}
</script>

{#snippet taskForm(
	formData: ReturnType<typeof createEmptyTask>,
	isEdit: boolean,
	useCustomAttempts: boolean,
	onToggleCustomAttempts: () => void,
	taskId?: number
)}
	<div class="flex flex-col gap-3">
		{#if isEdit}
			<p
				class="rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-400"
			>
				{$LL.tasks.editAnswerWarning()}
			</p>
		{/if}

		<!-- Question -->
		<div class="flex flex-col gap-1.5">
			<label for={isEdit ? `edit-task-question-${taskId}` : 'new-task-question'} class="form-label"
				>{$LL.tasks.question()}</label
			>
			<textarea
				id={isEdit ? `edit-task-question-${taskId}` : 'new-task-question'}
				bind:value={formData.question}
				placeholder={$LL.tasks.questionPlaceholder()}
				maxlength="500"
				rows="2"
				class="form-input"
			></textarea>
		</div>

		<!-- Answer Type -->
		<div class="flex flex-col gap-1.5">
			<label for="task-answer-type" class="form-label">{$LL.tasks.answerType()}</label>
			<Select id="task-answer-type" bind:value={formData.answer_type}>
				<option value="multiple_choice">{$LL.tasks.multipleChoice()}</option>
				<option value="string">{$LL.tasks.textAnswer()}</option>
				<option value="number">{$LL.tasks.numberAnswer()}</option>
			</Select>
		</div>

		<!-- MC Options -->
		{#if formData.answer_type === 'multiple_choice'}
			<div class="flex flex-col gap-2">
				<span class="form-label">{$LL.tasks.options()}</span>
				{#each formData.options as option, i (i)}
					<div class="flex items-center gap-2">
						<input
							type="checkbox"
							bind:checked={option.is_correct}
							class="cursor-pointer"
							title={$LL.tasks.markCorrect()}
						/>
						<input
							type="text"
							bind:value={option.label}
							placeholder="{$LL.tasks.optionLabel()} {i + 1}"
							maxlength="200"
							class="form-input flex-1"
						/>
						{#if formData.options.length > 2}
							<button
								type="button"
								onclick={() => removeOption(formData.options, i)}
								class="rounded p-1 text-red-500 transition hover:bg-red-500/10"
							>
								<DeleteIcon class="h-4 w-4" />
							</button>
						{/if}
					</div>
				{/each}
				<button
					type="button"
					onclick={() => addOption(formData.options)}
					class="flex w-fit btn-secondary items-center gap-1 text-xs"
				>
					<AddIcon class="h-3 w-3" />
					{$LL.tasks.addOption()}
				</button>
			</div>
		{/if}

		<!-- String Answer -->
		{#if formData.answer_type === 'string'}
			<div class="flex flex-col gap-1.5">
				<label for="task-correct-string" class="form-label">{$LL.tasks.correctAnswer()}</label>
				<input
					id="task-correct-string"
					type="text"
					bind:value={formData.correct_string_answer}
					class="form-input"
				/>
			</div>
			<div class="flex flex-col gap-1.5">
				<label for="task-match-mode" class="form-label">{$LL.tasks.matchMode()}</label>
				<Select id="task-match-mode" bind:value={formData.string_match_mode}>
					<option value="case_insensitive">{$LL.tasks.caseInsensitive()}</option>
					<option value="exact">{$LL.tasks.exactMatch()}</option>
				</Select>
				<p class="form-hint">
					{formData.string_match_mode === 'exact'
						? $LL.tasks.exactMatchHint()
						: $LL.tasks.caseInsensitiveHint()}
				</p>
			</div>
		{/if}

		<!-- Number Answer -->
		{#if formData.answer_type === 'number'}
			<div class="grid grid-cols-2 gap-3">
				<div class="flex flex-col gap-1.5">
					<label for="task-correct-number" class="form-label">{$LL.tasks.correctAnswer()}</label>
					<input
						id="task-correct-number"
						type="number"
						step="any"
						bind:value={formData.correct_number_answer}
						class="form-input"
					/>
				</div>
				<div class="flex flex-col gap-1.5">
					<label for="task-tolerance" class="form-label">{$LL.tasks.tolerance()}</label>
					<input
						id="task-tolerance"
						type="number"
						step="any"
						min="0"
						bind:value={formData.number_tolerance}
						placeholder={$LL.tasks.tolerancePlaceholder()}
						class="form-input"
					/>
				</div>
			</div>
		{/if}

		<!-- Points + Max Attempts -->
		<div class="flex flex-col gap-3">
			<div class="flex items-end gap-3">
				<div class="flex flex-col gap-1.5">
					<label for="task-points" class="form-label">{$LL.tasks.points()}</label>
					<input
						id="task-points"
						type="number"
						min="0"
						bind:value={formData.points}
						class="form-input w-24"
					/>
				</div>
			</div>

			<!-- Custom Max Attempts Toggle -->
			{#if useCustomAttempts}
				<div class="flex items-end gap-3">
					<div class="flex flex-col gap-1.5">
						<label for="task-max-attempts" class="form-label">{$LL.tasks.maxAttempts()}</label>
						<input
							id="task-max-attempts"
							type="number"
							min="1"
							bind:value={formData.max_attempts}
							class="form-input w-24"
						/>
					</div>
					<button
						type="button"
						onclick={onToggleCustomAttempts}
						class="mb-0.5 text-xs text-text/50 underline transition hover:text-text/70"
					>
						{$LL.cancel()}
					</button>
				</div>
			{:else}
				<button
					type="button"
					onclick={onToggleCustomAttempts}
					class="flex w-fit items-center gap-1 text-xs text-text/50 transition hover:text-text/70"
				>
					{$LL.tasks.usingDocumentDefault({ count: document.default_max_attempts })}
					&mdash;
					<span class="underline">{$LL.tasks.customRetryCount()}</span>
				</button>
			{/if}
		</div>
	</div>
{/snippet}

<div class="flex flex-col gap-4">
	<div class="flex items-center justify-between">
		<div class="form-label">{$LL.tasks.title()}</div>
		<button
			onclick={() => {
				newTask = createEmptyTask();
				newCustomAttempts = false;
				isAddingTask = !isAddingTask;
			}}
			class="flex btn-primary items-center gap-2 text-sm"
		>
			<AddIcon class="h-4 w-4" />
			{$LL.tasks.addTask()}
		</button>
	</div>

	<!-- Add Task Form -->
	{#if isAddingTask}
		<div class="flex flex-col gap-3 rounded-md border border-text/20 bg-text/5 p-4">
			<div class="text-sm font-semibold">{$LL.tasks.addTask()}</div>
			{@render taskForm(newTask, false, newCustomAttempts, () => {
				newCustomAttempts = !newCustomAttempts;
				if (!newCustomAttempts) {
					newTask.max_attempts = document.default_max_attempts;
				}
			})}
			<div class="flex items-center gap-2">
				<button onclick={createTask} class="flex btn-primary items-center gap-2 text-sm">
					<SaveIcon class="h-4 w-4" />
					{$LL.create()}
				</button>
				<button onclick={resetNewTaskForm} class="flex btn-secondary items-center gap-2 text-sm">
					<CancelIcon class="h-4 w-4" />
					{$LL.cancel()}
				</button>
			</div>
		</div>
	{/if}

	<!-- Tasks List -->
	<div
		class="flex flex-col gap-2"
		use:sortable={{ onReorder: handleReorder, enabled: tasks.length > 1 }}
	>
		{#if isLoading}
			<p class="text-muted">{$LL.loading()}</p>
		{:else if tasks.length === 0}
			<p class="text-muted">{$LL.tasks.noTasks()}</p>
		{:else}
			{#each tasks as task (task.id)}
				{#if editingTaskId === task.id}
					<!-- Edit Form -->
					<div
						data-sortable-id={task.id}
						class="flex flex-col gap-3 rounded-md border border-text/20 bg-text/5 p-4"
					>
						<div class="text-sm font-semibold">{$LL.tasks.editTask()}</div>
						{@render taskForm(
							editTask,
							true,
							editCustomAttempts,
							() => {
								editCustomAttempts = !editCustomAttempts;
								if (!editCustomAttempts) {
									editTask.max_attempts = document.default_max_attempts;
								}
							},
							task.id
						)}
						<div class="flex items-center gap-2">
							<button
								onclick={() => updateTask(task.id)}
								class="flex btn-primary items-center gap-2 text-sm"
							>
								<SaveIcon class="h-4 w-4" />
								{$LL.saveChanges()}
							</button>
							<button onclick={cancelEdit} class="flex btn-secondary items-center gap-2 text-sm">
								<CancelIcon class="h-4 w-4" />
								{$LL.cancel()}
							</button>
						</div>
					</div>
				{:else}
					<!-- Task Display -->
					<div
						data-sortable-id={task.id}
						class="flex items-center gap-3 rounded-md border border-text/20 bg-text/5 p-3 transition hover:border-text/30"
					>
						<span
							data-drag-handle
							class="flex cursor-grab items-center text-text/40 hover:text-text/70"
						>
							<DragIcon class="h-5 w-5" />
						</span>
						<div class="flex-1">
							<p class="text-sm font-semibold">{task.question}</p>
							<div class="mt-1 flex flex-wrap gap-2">
								<span class="rounded bg-text/10 px-2 py-0.5 text-xs text-text/70">
									{answerTypeLabel(task.answer_type as AnswerType)}
								</span>
								<span class="rounded bg-primary/20 px-2 py-0.5 text-xs text-primary">
									{task.points}
									{$LL.points()}
								</span>
								<span class="rounded bg-text/10 px-2 py-0.5 text-xs text-text/70">
									{$LL.tasks.triesCount({ count: task.max_attempts })}
								</span>
							</div>
						</div>
						<div class="flex items-center gap-1">
							<button onclick={() => startEditingTask(task)} class="btn-ghost">
								<EditIcon class="h-4 w-4" />
							</button>
							<ConfirmButton onConfirm={() => deleteTask(task.id)}>
								{#snippet button()}
									<div class="btn-ghost">
										<DeleteIcon class="h-4 w-4 text-red-600" />
									</div>
								{/snippet}
								{#snippet slideout()}
									<div
										class="rounded-md bg-red-500/10 px-3 py-2 whitespace-nowrap text-red-600 dark:text-red-400"
									>
										{$LL.tasks.deleteConfirm()}
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
