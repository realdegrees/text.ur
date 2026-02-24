<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLSelectAttributes } from 'svelte/elements';

	interface Props extends HTMLSelectAttributes {
		children: Snippet;
		class?: string;
		value?: string | number | null;
	}

	let { children, class: className = '', value = $bindable(), ...rest }: Props = $props();
</script>

<select
	class="rounded border border-text/15 bg-inset px-3 py-1.5 text-sm text-text transition outline-none focus:border-primary/50 disabled:opacity-50 {className}"
	bind:value
	{...rest}
>
	{@render children()}
</select>
