<script lang="ts">
	import Arrow from '~icons/material-symbols/arrow-back-ios-new-rounded';
	let { expanded = $bindable(false), label = '' }: { expanded: boolean; label: string } = $props();
</script>

<button
	class="card-black group mr-auto flex items-center justify-center gap-2 rounded-md bg-primary p-2! py-1! hover:brightness-105"
	onclick={() => (expanded = !expanded)}
>
	{#if expanded}
		<span>Hide {label}</span>
	{:else}
		<span>Show {label}</span>
	{/if}
	<Arrow
		class="-rotate-180 transition-all {expanded &&
			'-rotate-90!'} mt-px h-full group-hover:scale-110 group-hover:animate-pulse"
	/>
</button>
