<script lang="ts">
	import CalendarIcon from '~icons/material-symbols/calendar-month-outline';
	import ClearIcon from '~icons/material-symbols/close-rounded';
	import { formatDateTime, getCurrentDateTimeLocal } from '$lib/util/dateFormat';

	let {
		value = $bindable<string | null>(null),
		label = 'Expiration',
		id
	}: {
		value?: string | null;
		label?: string;
		id?: string;
	} = $props();

	let inputRef: HTMLInputElement;
	let minDateTime = getCurrentDateTimeLocal();

	const openPicker = () => {
		inputRef?.showPicker?.();
	};

	const clearDate = () => {
		value = null;
	};
</script>

<div class="flex flex-col gap-2">
	<label for={id} class="text-xs font-semibold text-text/70">{label}</label>

	<div class="relative flex items-center gap-2">
		<!-- Display field (clickable to open picker) -->
		<button
			type="button"
			onclick={openPicker}
			class="flex-1 rounded border border-text/20 bg-background px-3 py-2 text-left text-sm transition-colors hover:border-text/30 {!value
				? 'text-text/50'
				: 'text-text'}"
		>
			{formatDateTime(value)}
		</button>

		<!-- Calendar button -->
		<button
			type="button"
			onclick={openPicker}
			class="flex items-center justify-center rounded border border-text/20 bg-background p-2 text-text/50 transition-colors hover:border-text/30 hover:text-text"
			title="Select date and time"
		>
			<CalendarIcon class="h-5 w-5" />
		</button>

		<!-- Clear button (only shown when date is set) -->
		{#if value}
			<button
				type="button"
				onclick={clearDate}
				class="flex items-center justify-center rounded border border-text/20 bg-background p-2 text-text/50 transition-colors hover:border-text/30 hover:text-red-500"
				title="Clear expiration (never expires)"
			>
				<ClearIcon class="h-5 w-5" />
			</button>
		{/if}

		<!-- Positioned datetime input for picker -->
		<input
			bind:this={inputRef}
			{id}
			type="datetime-local"
			bind:value
			min={minDateTime}
			class="pointer-events-none absolute top-[50%] left-0 z-0 h-0 w-0 opacity-0"
		/>
	</div>
</div>
