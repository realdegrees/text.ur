<script lang="ts" generics="Item extends unknown">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import type { Paginated } from '$api/pagination';
	import type { Snippet } from 'svelte';
	import Arrow from '~icons/material-symbols/arrow-forward-ios-rounded';

	let {
		itemSnippet,
		data
	}: {
		itemSnippet: Snippet<[Item]>;
		data: Paginated<Item>;
	} = $props();
	let {
		data: items,
		limit,
		offset,
		total,
		currentPage,
		maxPages
	} = $derived({
		...data,
		maxPages: Math.ceil(data.total / data.limit),
		currentPage: Math.floor(data.offset / data.limit) + 1
	});

	function changePage(direction: -1 | 1) {
		const delta = limit * direction;
		const newOffset = Math.max(0, Math.min(total - 1, offset + delta));
		page.url.searchParams.set('offset', `${newOffset}`);
		goto(page.url, { invalidateAll: true });
	}
</script>

<!-- Item List -->
<ul class="w-full">
	{#each items as item (item)}
		<li class="mt-1">
			{@render itemSnippet(item as Item)}
		</li>
	{/each}
</ul>

<!-- Page Controls -->
<div class="flex flex-row items-stretch justify-start w-full">
	<div class="flex flex-row justify-center w-full items-center">
		<button class:invisible={currentPage === 1} onclick={() => changePage(-1)}
			><Arrow class="rotate-180" /></button
		>
		<span>Page {currentPage} of {maxPages}</span>
		<button class:invisible={currentPage === maxPages} onclick={() => changePage(+1)}
			><Arrow /></button
		>
	</div>
	<div class="flex flex-row items-center gap-1">
		<label for="itemsPerPage" class="whitespace-nowrap">Entries per page:</label>
		<select
			id="itemsPerPage"
			class="bg-background rounded py-0.5"
			onchange={({ currentTarget: { value } }) => {
				page.url.searchParams.set('limit', `${value}`);
				page.url.searchParams.set('offset', `${0}`);
				goto(page.url, { invalidateAll: true });
			}}
		>
			{#each [10, 25, 50, 100] as option (option)}
				<option class="bg-background" value={option} selected={option === limit}>{option}</option>
			{/each}
		</select>
	</div>
</div>
