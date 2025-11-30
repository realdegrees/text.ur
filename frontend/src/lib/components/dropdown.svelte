<script lang="ts" generics="Item extends unknown">
	import { slide } from 'svelte/transition';
	import { quintInOut } from 'svelte/easing';
	import type { Snippet } from 'svelte';
	import { tick } from 'svelte';
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
		showArrow = true,
		allowSelection = true, // New flag to control selection toggle visibility
		showCurrentItemInList = false, // Flag to control whether to show current item in dropdown list
		// no appendToBody prop - always render menu as fixed overlay
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
		allowSelection?: boolean; // Add type for the new flag
		showCurrentItemInList?: boolean; // Flag to show current item in list
		// Removed appendToBody prop - always render menu as fixed overlay
	} = $props();

	let dropdownRef: HTMLDivElement;
	let menuRef = $state<HTMLDivElement>();
	let menuStyle = $state('');

	function toggleDropdown() {
		show = !show;
	}

	function handleItemSelect(item: Item) {
		currentItem = item;
		show = false;
		onSelect?.(item);
	}

	let arrowRef = $state<HTMLElement>();

	// Close dropdown when clicking outside
	function handleClickOutside(event: MouseEvent) {
		if (
			dropdownRef &&
			!dropdownRef.contains(event.target as Node) &&
			!(menuRef && menuRef.contains(event.target as Node))
		) {
			show = false;
		}
	}

	async function updateMenuPosition() {
		if (!dropdownRef || !menuRef) return;
		await tick();
		const rect = dropdownRef.getBoundingClientRect();
		const menuRect = menuRef.getBoundingClientRect();
		const styles: Record<string, string> = {};

		const gapTop = 0;
		const gapBottom = 6;

		if (position.includes('left')) {
			let left = rect.left;
			left = Math.max(8, Math.min(left, window.innerWidth - menuRect.width - 8));
			styles.left = `${left}px`;
		} else {
			let left = rect.right - menuRect.width;
			left = Math.max(8, Math.min(left, window.innerWidth - menuRect.width - 8));
			styles.left = `${left}px`;
		}

		if (position.includes('top')) {
			let top = rect.top - menuRect.height - gapTop;
			// Ensure the dropdown is strictly above the trigger
			top = Math.max(8, top);
			styles.top = `${top}px`;
			styles.transformOrigin = position.includes('right') ? 'bottom right' : 'bottom left';
		} else {
			let top = rect.bottom + gapBottom;
			// Ensure the dropdown is strictly below the trigger
			top = Math.min(Math.max(8, top), window.innerHeight - menuRect.height - 8);
			styles.top = `${top}px`;
			styles.transformOrigin = position.includes('right') ? 'top right' : 'top left';
		}

		menuStyle = Object.entries(styles).map(([k, v]) => `${k}: ${v};`).join(' ');

		// Detailed debug logs
		console.log('Dropdown position:', position);
		console.log('Trigger rect:', rect);
		console.log('Menu rect:', menuRect);
		console.log('Computed styles:', styles);
		console.log('Final menuStyle:', menuStyle);
	}

	$effect(() => {
		if (show) {
			document.addEventListener('click', handleClickOutside);
			updateMenuPosition();
			window.addEventListener('resize', updateMenuPosition);
			window.addEventListener('scroll', updateMenuPosition, true);
		} else {
			document.removeEventListener('click', handleClickOutside);
			window.removeEventListener('resize', updateMenuPosition);
			window.removeEventListener('scroll', updateMenuPosition, true);
		}

		return () => {
			document.removeEventListener('click', handleClickOutside);
			window.removeEventListener('resize', updateMenuPosition);
			window.removeEventListener('scroll', updateMenuPosition, true);
		};
	});
</script>

<div class="relative" bind:this={dropdownRef}>
	{#if allowSelection}
		<!-- Check the allowSelection flag -->
		<button
			type="button"
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
	{/if}

	{#if show}
		<div
			bind:this={menuRef}
			class="bg-surface fixed z-50 min-w-max rounded-sm border border-text/50 bg-background shadow-lg"
			style={menuStyle}
			transition:slide={{ duration: 200, easing: quintInOut }}
		>
			{#each items.filter((item) => showCurrentItemInList || item !== currentItem) as item (item)}
				<button
					type="button"
					class="block w-full whitespace-nowrap hover:bg-primary"
					onclick={() => handleItemSelect(item)}
				>
					{@render itemSnippet(item)}
				</button>
			{/each}
		</div>
	{/if}
</div>
