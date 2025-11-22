<script lang="ts">
	import CheckIcon from '~icons/material-symbols/check';
	import DeleteIcon from '~icons/material-symbols/delete-outline';

	interface Props {
		isOpen: boolean;
		disabled?: boolean;
		size?: 'sm' | 'md';
		onConfirm: () => void;
		onOpen: () => void;
		onClose: () => void;
	}

	let {
		isOpen,
		disabled = false,
		size = 'md',
		onConfirm,
		onOpen,
		onClose
	}: Props = $props();

	let containerRef: HTMLDivElement | null = $state(null);

	// Close when clicking outside
	$effect(() => {
		if (!isOpen) return;

		const handleClickOutside = (e: MouseEvent) => {
			if (containerRef && !containerRef.contains(e.target as Node)) {
				onClose();
			}
		};

		// Use setTimeout to avoid the click that opened the confirm from immediately closing it
		// Use capture phase to catch clicks before stopPropagation prevents bubbling
		const timeoutId = setTimeout(() => {
			document.addEventListener('click', handleClickOutside, true);
		}, 0);

		return () => {
			clearTimeout(timeoutId);
			document.removeEventListener('click', handleClickOutside, true);
		};
	});

	const iconSize = $derived(size === 'sm' ? 'h-3 w-3' : 'h-3.5 w-3.5');
	const padding = $derived(size === 'sm' ? 'px-1 py-0.5' : 'px-1.5 py-0.5');
	const buttonPadding = $derived(size === 'sm' ? 'p-0.5' : 'p-1');
</script>

<div class="relative" bind:this={containerRef}>
	{#if isOpen}
		<div class="flex items-center gap-1 rounded bg-red-500/10 {padding}">
			<span class="text-xs text-red-400">Delete?</span>
			<button
				class="rounded p-0.5 text-red-400 transition-colors hover:bg-red-500/20 hover:text-red-500"
				onclick={(e) => { e.stopPropagation(); onConfirm?.(); }}
				title="Confirm delete"
				{disabled}
			>
				<CheckIcon class={iconSize} />
			</button>
		</div>
	{:else}
		<button
			class="rounded {buttonPadding} text-text/40 transition-colors hover:bg-red-500/20 hover:text-red-500"
			onclick={(e) => { e.stopPropagation(); onOpen?.(); }}
			title="Delete"
			{disabled}
		>
			<DeleteIcon class={iconSize} />
		</button>
	{/if}
</div>
