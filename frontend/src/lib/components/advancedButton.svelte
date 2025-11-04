<script lang="ts">
	import type { Component, Snippet } from 'svelte';
	import type { MouseEventHandler, SVGAttributes } from 'svelte/elements';
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
		Icon?: Component<SVGAttributes<SVGSVGElement>>;
		type?: 'button' | 'reset' | 'submit';
		absoluteSlideout?: boolean;
		componentClass?: string;
		slideOutDirection?: -1 | 1;
	} = $props();
	let hovered = $state(false);
</script>

<button
	{disabled}
	class="w-fit flex flex-row items-center rounded-none! shadow-none! group p-0!"
	{type}
	onmouseenter={() => (hovered = true)}
	onmouseleave={() => (hovered = false)}
	{onclick}
>
	{#if (permanentSlideout || hovered) && slideOutText.trim().length}
		<p
			transition:fly={{ x: -20 * slideOutDirection, duration: 90, opacity: 0 }}
			class="{absoluteSlideout &&
				`absolute top-0 h-full ${slideOutDirection > 0 ? 'left-0' : 'right-0'}`} whitespace-nowrap w-fit pr-2 group-hover:scale-[95%] transition-all"
		>
			{slideOutText.trim()}
		</p>
	{/if}
	<div class="bg-primary card-black p-1! rounded w-full h-full {componentClass}">
		{@render children?.()}
	</div>
</button>
