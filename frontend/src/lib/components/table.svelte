<script lang="ts" generics="RowItem extends Record<string, any>">
	import type { Snippet } from 'svelte';
	import AdvancedButton from './advancedButton.svelte';

	type Column<T extends RowItem = RowItem> = {
		label: string;
		selectsRow?: boolean;
		content: Snippet<[T]>;
		contentCondition?: (item: T) => boolean;
		onCellClick?: (item: T) => void;
		alignment: 'left' | 'center' | 'right';
		slideOutText?: string;
		cellStyle?: string;
	};

	let {
		rowItems = [],
		selected = $bindable([]),
		columns = []
	}: {
		rowItems: RowItem[];
		columns: Column[];
		selected: RowItem[];
	} = $props();

	function toggleFileSelection(rowItem: RowItem) {
		if (selected.find(({ id }) => id === rowItem.id)) {
			selected = selected.filter(({ id }) => id !== rowItem.id);
		} else {
			selected = [...selected, rowItem];
		}
	}
</script>

{#snippet Section(columns: Column[], rowItem: RowItem)}
	<div class="flex items-center justify-center gap-2">
		{#each columns.filter(({ contentCondition }) => !contentCondition || contentCondition(rowItem)) as column (column.label)}
			<AdvancedButton
				disabled={!column.onCellClick && !column.selectsRow}
				onclick={() => {
					column.onCellClick?.(rowItem);
					if (column.selectsRow) {
						toggleFileSelection(rowItem);
					}
				}}
				componentClass={column.cellStyle}
				slideOutText={column.slideOutText}
			>
				{@render column.content(rowItem)}
			</AdvancedButton>
		{/each}
	</div>
{/snippet}

<ul class="w-full">
	{#each rowItems as rowItem (rowItem.id)}
		{@const isSelected = selected.find(({ id }) => id === rowItem.id)}
		<li class="flex items-center justify-between bg-accent p-2" class:opacity-30={isSelected}>
			{@render Section(
				columns.filter(({ alignment }) => alignment === 'left'),
				rowItem
			)}
			{@render Section(
				columns.filter(({ alignment }) => alignment === 'center'),
				rowItem
			)}
			{@render Section(
				columns.filter(({ alignment }) => alignment === 'right'),
				rowItem
			)}
		</li>
	{/each}
</ul>

<style lang="postcss">
	@reference '../../app.css';

	li:nth-child(even) {
		@apply brightness-105;
	}
	li:last-child {
		@apply rounded-b;
	}
	li:first-child {
		@apply rounded-t;
	}
</style>
