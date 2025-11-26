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

	let containerRef: HTMLDivElement | null = null;
	let isOpen = $state(false);

	function confirm() {
		onConfirm?.();
		close();
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') close();
	}
</script>

<svelte:window on:keydown={handleKeydown} />

<div
	class="flex flex-{slideoutDirection == 'right' ? 'row' : 'row-reverse'} overflow-hidden rounded"
	bind:this={containerRef}
>
	<!-- render the passed snippets using Svelte snippets API -->
	<button
		onclick={() => {
			if (isOpen) {
				confirm();
				isOpen = false;
			} else {
				isOpen = true;
			}
		}}
		onfocusout={() => (isOpen = false)}
		{disabled}
	>
		{@render button?.(isOpen)}
	</button>

	{#if isOpen}
		{#if slideout}
			{@render slideout()}
		{:else}
			<span class="text-text/60 text-xs">Confirm?</span>
		{/if}
	{/if}
</div>
