<script lang="ts">
	import type { Snippet } from 'svelte';

	// Use $props pattern for consistency with codebase
	let {
		button,
		slideout,
		slideoutDirection = 'left',
		disabled = false,
		onConfirm
	}: {
		button?: Snippet<[boolean]>;
		slideout?: Snippet<[]>;
		slideoutDirection?: 'left' | 'right';
		disabled?: boolean;
		onConfirm?: () => void;
	} = $props();

	let isOpen = $state(false);

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') isOpen = false;
	}
</script>

<svelte:window on:keydown={handleKeydown} />

<div
	class="flex flex-{slideoutDirection == 'right' ? 'row' : 'row-reverse'} overflow-hidden rounded"
>
	<!-- render the passed snippets using Svelte snippets API -->
	<button
		onclick={() => {
			if (isOpen) {
				onConfirm?.();
				isOpen = false;
			} else {
				isOpen = true;
			}
		}}
		onfocusout={() => (isOpen = false)}
		{disabled}
		class="grow"
	>
		{@render button?.(isOpen)}
	</button>

	{#if isOpen}
		{#if slideout}
			{@render slideout()}
		{:else}
			<span class="text-xs text-text/60">Confirm?</span>
		{/if}
	{/if}
</div>
