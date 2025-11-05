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
	class="card-black flex h-6 w-6 items-center justify-center rounded-md bg-accent p-px!"
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
			<Enabled class="h-full w-full" />
		</div>
	{:else if value === (invert ? true : false)}
		<div transition:slide={{ axis: 'y', duration: 120 }}>
			<Disabled class="h-full w-full" />
		</div>
	{/if}
</button>
