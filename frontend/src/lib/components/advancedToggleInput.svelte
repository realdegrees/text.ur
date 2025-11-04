<script lang="ts">
	import Disabled from '~icons/iconoir/xmark';
	import Enabled from '~icons/iconoir/check';
	import { slide } from 'svelte/transition';

	let {
		value = $bindable(undefined),
		invert = false,
		allowUnset = false,
		onClick
	}: {
		value?: boolean | null | undefined;
		allowUnset?: boolean;
		invert?: boolean;
		onClick?: (value?: boolean) => void;
	} = $props();
</script>

<button
	class="flex justify-center items-center rounded-md w-6 h-6 p-px! card-black bg-accent"
	type="button"
	onclick={() => {
		if (value === undefined || value === null) value = !invert;
		else if (value === !invert) value = invert;
		else if (value === invert) value = allowUnset ? undefined : !invert;
		onClick?.(value);
	}}
>
	{#if value === (invert ? false : true)}
		<div transition:slide={{ axis: 'y', duration: 120 }}>
			<Enabled class="w-full h-full" />
		</div>
	{:else if value === (invert ? true : false)}
		<div transition:slide={{ axis: 'y', duration: 120 }}>
			<Disabled class="w-full h-full" />
		</div>
	{/if}
</button>
