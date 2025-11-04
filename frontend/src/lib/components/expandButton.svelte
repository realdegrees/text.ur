<script lang="ts">
	import Arrow from '~icons/material-symbols/arrow-back-ios-new-rounded';
	let { expanded = $bindable(false), label = '' }: { expanded: boolean; label: string } = $props();
</script>

<button
	class="bg-primary card-black p-2! py-1! rounded-md flex items-center justify-center gap-2 mr-auto group hover:brightness-105"
	onclick={() => (expanded = !expanded)}
>
	{#if expanded}
		<span>Hide {label}</span>
	{:else}
		<span>Show {label}</span>
	{/if}
	<Arrow
		class="transition-all -rotate-180 {expanded &&
			'-rotate-90!'} group-hover:scale-110 group-hover:animate-pulse h-full mt-px"
	/>
</button>
