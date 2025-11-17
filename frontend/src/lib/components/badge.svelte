<script lang="ts" generics="T">
	import RemoveIcon from "~icons/material-symbols/close-rounded";
	import { scale } from "svelte/transition";

	interface BadgeProps<T> {
		item: T;
		label: string;
		showRemove?: boolean;
		onRemove?: (item: T) => void;
		disabled?: boolean;
	}

	let { item, label, showRemove = true, onRemove, disabled = false }: BadgeProps<T> = $props();

	function handleRemove(): void {
		if (onRemove) {
			onRemove(item);
		}
	}
</script>

<div
	class="bg-background text-text h-5.5 flex flex-row items-center rounded text-xs shadow-inner shadow-black/30"
	in:scale
	out:scale
>
	<p class="whitespace-nowrap p-1.5">{label}</p>
	{#if showRemove}
		<button
			onclick={handleRemove}
			class="h-full w-full rounded-r bg-black/10 shadow-black/20 transition-all hover:cursor-pointer hover:bg-red-500/30 hover:shadow-inner"
			aria-label="Remove {label}"
			type="button"
			{disabled}
		>
			<RemoveIcon class="h-full w-full" />
		</button>
	{/if}
</div>
