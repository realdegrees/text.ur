<script lang="ts" generics="T">
	import RemoveIcon from '~icons/material-symbols/close-rounded';
	import { scale } from 'svelte/transition';

	interface BadgeProps<T> {
		item: T;
		label: string;
		showRemove?: boolean;
		onRemove?: (item: T) => void;
		disabled?: boolean;
		customColor?: string;
	}

	let {
		item,
		label,
		showRemove = true,
		onRemove,
		disabled = false,
		customColor
	}: BadgeProps<T> = $props();
</script>

<div
	class="flex h-5.5 flex-row items-center rounded text-xs text-text shadow-inner shadow-black/30"
	class:bg-background={!customColor}
	style={customColor ? `background-color: ${customColor}` : ''}
	in:scale
	out:scale
>
	<p class="p-1.5 whitespace-nowrap">{label}</p>
	{#if showRemove}
		<button
			onclick={() => onRemove?.(item)}
			class="h-full w-full rounded-r bg-black/10 shadow-black/20 transition-all hover:cursor-pointer hover:bg-red-500/30 hover:shadow-inner"
			aria-label="Remove {label}"
			type="button"
			{disabled}
		>
			<RemoveIcon class="h-full w-full" />
		</button>
	{/if}
</div>
