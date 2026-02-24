<script lang="ts">
	import type { Snippet } from 'svelte';
	import HelpIcon from '~icons/material-symbols/help-outline';
	import InfoIcon from '~icons/material-symbols/info-outline';

	interface Props {
		icon?: 'help' | 'info';
		children: Snippet;
		class?: string;
		iconSize?: string;
	}

	let {
		icon = 'help',
		children,
		class: className = '',
		iconSize = 'h-3.5 w-3.5'
	}: Props = $props();

	let showTooltip = $state(false);
	let hideTimeout: ReturnType<typeof setTimeout> | null = null;
	let triggerRef: HTMLDivElement | null = $state(null);
	let tooltipStyle = $state('');

	const IconComponent = $derived(icon === 'help' ? HelpIcon : InfoIcon);

	function show() {
		if (hideTimeout) {
			clearTimeout(hideTimeout);
			hideTimeout = null;
		}
		if (triggerRef) {
			const rect = triggerRef.getBoundingClientRect();
			tooltipStyle = `top: ${rect.top}px; left: ${rect.right + 6}px;`;
		}
		showTooltip = true;
	}

	function hide() {
		hideTimeout = setTimeout(() => {
			showTooltip = false;
		}, 150);
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') showTooltip = false;
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="relative inline-flex" bind:this={triggerRef} onmouseenter={show} onmouseleave={hide}>
	<button
		type="button"
		class="text-text/40 transition-colors hover:text-text/70 {className}"
		onclick={(e) => e.stopPropagation()}
	>
		<IconComponent class={iconSize} />
	</button>

	{#if showTooltip}
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="fixed z-9999 w-64 rounded border border-text/20 bg-background p-2 text-xs shadow-lg"
			style={tooltipStyle}
			onmouseenter={show}
			onmouseleave={hide}
			onmousedown={(e) => e.preventDefault()}
		>
			{@render children()}
		</div>
	{/if}
</div>
