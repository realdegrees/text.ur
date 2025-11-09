<script lang="ts" generics="Item extends unknown">
	import { slide } from 'svelte/transition';
	import { quintInOut } from 'svelte/easing';
	import type { Snippet } from 'svelte';
	import ChevronDown from '~icons/material-symbols/keyboard-arrow-down';

	let {
		items,
		itemSnippet,
		currentItem = $bindable(),
		itemTextMap,
		onSelect,
		show = $bindable(false),
		position = 'bottom-left',
		title,
		icon,
		hideCurrentSelection = false,
		showArrow = true
	}: {
		items: Item[];
		itemSnippet: Snippet<[Item]>;
		currentItem?: Item;
		itemTextMap?: (item: Item) => string;
		onSelect?: (item: Item) => void;
		show?: boolean;
		position?: 'bottom-left' | 'bottom-right' | 'top-left' | 'top-right';
		title?: string;
		icon?: Snippet;
		hideCurrentSelection?: boolean;
		showArrow?: boolean;
	} = $props();

	let dropdownRef: HTMLDivElement;

	function toggleDropdown() {
		show = !show;
	}

	function handleItemSelect(item: Item) {
		currentItem = item;
		show = false;
		onSelect?.(item);
	}

	let arrowRef = $state<HTMLElement>();

	function getArrowPosition() {
		if (!arrowRef || !dropdownRef) return { left: 0 };

		const dropdownRect = dropdownRef.getBoundingClientRect();
		const arrowRect = arrowRef.getBoundingClientRect();

		return {
			left: arrowRect.left - dropdownRect.left + arrowRect.width / 2
		};
	}

	// Close dropdown when clicking outside
	function handleClickOutside(event: MouseEvent) {
		if (dropdownRef && !dropdownRef.contains(event.target as Node)) {
			show = false;
		}
	}

	$effect(() => {
		if (show) {
			document.addEventListener('click', handleClickOutside);
		} else {
			document.removeEventListener('click', handleClickOutside);
		}

		return () => {
			document.removeEventListener('click', handleClickOutside);
		};
	});
</script>

<div class="relative" bind:this={dropdownRef}>
	<button
		class="bg-surface hover:bg-surface-variant flex cursor-pointer items-center justify-between gap-1 rounded-sm"
		onclick={toggleDropdown}
		{title}
	>
		{#if icon}
			{@render icon()}
		{/if}

		{#if !hideCurrentSelection && currentItem && itemTextMap}
			<span class="text-sm">{itemTextMap(currentItem)}</span>
		{/if}

		{#if showArrow}
			<div bind:this={arrowRef} class:rotate-180={show} class="transition-transform duration-200">
				<ChevronDown class="h-4 w-4" />
			</div>
		{/if}
	</button>

	{#if show}
		<div
			class="bg-surface absolute z-50 min-w-max rounded-sm border border-text/50 bg-background shadow-lg"
			style:left="{getArrowPosition().left}px"
			style:top={position.includes('top') ? 'auto' : '100%'}
			style:bottom={position.includes('top') ? '100%' : 'auto'}
			style:transform="translateX(-50%)"
			transition:slide={{ duration: 200, easing: quintInOut }}
		>
			{#each items.filter((item) => item !== currentItem) as item (item)}
				<button
					class="block w-full whitespace-nowrap hover:bg-primary"
					onclick={() => handleItemSelect(item)}
				>
					{@render itemSnippet(item)}
				</button>
			{/each}
		</div>
	{/if}
</div>
