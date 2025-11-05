<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { MouseEventHandler } from 'svelte/elements';
	import { fly } from 'svelte/transition';
	// import Missing from '~icons/material-symbols/indeterminate-question-box-rounded';

	let {
		onclick,
		slideOutText = '',
		permanentSlideout = false,
		componentClass = '',
		type = 'button',
		absoluteSlideout = false,
		slideOutDirection = -1,
		disabled = false,
		children
	}: {
		children?: Snippet<[]>;
		disabled?: boolean;
		permanentSlideout?: boolean;
		onclick?: MouseEventHandler<HTMLButtonElement> | null | undefined;
		slideOutText?: string;
		type?: 'button' | 'reset' | 'submit';
		absoluteSlideout?: boolean;
		componentClass?: string;
		slideOutDirection?: -1 | 1;
	} = $props();
	let hovered = $state(false);
</script>

<button
	{disabled}
	class="group flex w-fit flex-row items-center rounded-none! p-0! shadow-none!"
	{type}
	onmouseenter={() => (hovered = true)}
	onmouseleave={() => (hovered = false)}
	{onclick}
>
	{#if (permanentSlideout || hovered) && slideOutText.trim().length}
		<p
			transition:fly={{ x: -20 * slideOutDirection, duration: 90, opacity: 0 }}
			class="{absoluteSlideout &&
				`absolute top-0 h-full ${slideOutDirection > 0 ? 'left-0' : 'right-0'}`} w-fit pr-2 whitespace-nowrap transition-all group-hover:scale-[95%]"
		>
			{slideOutText.trim()}
		</p>
	{/if}
	<div class="card-black h-full w-full rounded bg-primary p-1! {componentClass}">
		{@render children?.()}
	</div>
</button>
