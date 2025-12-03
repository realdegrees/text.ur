<script lang="ts">
	import ZoomInIcon from '~icons/material-symbols/zoom-in';
	import ZoomOutIcon from '~icons/material-symbols/zoom-out';
	import FitPageIcon from '~icons/material-symbols/fit-page';
	import ChevronUpIcon from '~icons/material-symbols/keyboard-arrow-up';
	import ChevronDownIcon from '~icons/material-symbols/keyboard-arrow-down';
	import ExpandIcon from '~icons/material-symbols/chevron-right';
	import CollapseIcon from '~icons/material-symbols/chevron-left';
	import CursorIcon from '~icons/material-symbols/near-me';
	import ViewModeSelector from './ViewModeSelector.svelte';
	import FilterList from './FilterList.svelte';
	import { documentStore, type FilterState } from '$lib/runes/document.svelte.js';
	import { documentWebSocket } from '$lib/stores/documentWebSocket.svelte';
	import { sessionStore } from '$lib/runes/session.svelte';
	import PersonIcon from '~icons/material-symbols/person';
	import ClearFilterIcon from '~icons/mdi/filter-remove-outline';
	import { scale } from 'svelte/transition';

	interface Props {
		minScale: number;
		maxScale: number;
		pageNumber: number;
		numPages: number;
		onZoomIn: () => void;
		onZoomOut: () => void;
		onFitHeight: () => void;
		onPrevPage: () => void;
		onNextPage: () => void;
	}

	let {
		minScale,
		maxScale,
		pageNumber,
		numPages,
		onZoomIn,
		onZoomOut,
		onFitHeight,
		onPrevPage,
		onNextPage
	}: Props = $props();

	let isExpanded = $state(true);

	const buttonClass =
		'rounded p-2 text-text/70 transition-colors hover:bg-text/10 hover:text-text disabled:opacity-30 disabled:hover:bg-transparent';
	const activeButtonClass =
		'rounded p-2 text-primary bg-primary/10 transition-colors hover:bg-primary/20';

	const activeUserFilters = $derived.by(() => {
		return documentWebSocket.activeUsers.map(({ user_id, username }) => {
			const existingFilter = documentStore.filters.get('author', user_id);
			return {
				id: user_id,
				data: { username: username },
				type: 'author',
				value: existingFilter?.value
			} as FilterState<'author'>;
		});
	});

	const documentAuthorFilters = $derived.by(() => {
		return documentStore.comments.topLevelAuthors
			.map((user) => {
				const existingFilter = documentStore.filters.get('author', user.id);
				return {
					id: user.id,
					data: user,
					type: 'author',
					value: existingFilter?.value
				} as FilterState<'author'>;
			})
			.filter(({ id }) => !activeUserFilters.some((u) => u.id === id));
	});

	const tagFilters = $derived.by(() => {
		return (
			documentStore.loadedDocument?.tags.map((tag) => {
				const existingFilter = documentStore.filters.get('tag', tag.id);
				return {
					id: tag.id,
					data: { label: tag.label, color: tag.color },
					type: 'tag',
					value: existingFilter?.value
				} as FilterState<'tag'>;
			}) ?? []
		);
	});

	const anyFilterActive = $derived.by(() => {
		return documentStore.filters.all.length > 0;
	});

	// Get initials from username
	const getInitials = (username: string): string => {
		return username.slice(0, 2).toUpperCase();
	};

	// Generate a consistent color based on user ID
	const getUserColor = (userId: number): string => {
		const colors = [
			'bg-blue-500',
			'bg-green-500',
			'bg-purple-500',
			'bg-orange-500',
			'bg-pink-500',
			'bg-teal-500',
			'bg-indigo-500',
			'bg-rose-500'
		];
		return colors[userId % colors.length];
	};
</script>

<div
	class="no-scrollbar border-text/10 bg-inset flex shrink-0 flex-col overflow-y-auto overflow-x-hidden border-r transition-all duration-200 {isExpanded
		? 'w-40'
		: 'w-12'}"
>
	<!-- Expand/Collapse Button -->
	<button
		class="border-text/10 text-text/50 hover:bg-text/5 hover:text-text/70 flex items-center justify-center gap-2 border-b p-2 transition-colors"
		onclick={() => (isExpanded = !isExpanded)}
		title={isExpanded ? 'Collapse' : 'Expand'}
	>
		{#if isExpanded}
			<CollapseIcon class="h-4 w-4" />
			<span class="text-xs">Collapse</span>
		{:else}
			<ExpandIcon class="h-4 w-4" />
		{/if}
	</button>

	<div class="flex flex-col items-center gap-1 py-3 {isExpanded ? 'px-2' : ''}">
		<!-- Zoom Controls -->
		<div class="flex {isExpanded ? 'w-full justify-between' : 'flex-col'} items-center gap-1">
			<button
				class="{buttonClass} {isExpanded ? 'flex-1' : ''}"
				onclick={onZoomIn}
				disabled={documentStore.documentScale >= maxScale}
				title="Zoom In"
			>
				<span class="flex items-center gap-2">
					<ZoomInIcon class="h-5 w-5" />
					{#if isExpanded}<span class="text-xs">Zoom In</span>{/if}
				</span>
			</button>
			<button
				class="{buttonClass} {isExpanded ? 'flex-1' : ''}"
				onclick={onZoomOut}
				disabled={documentStore.documentScale <= minScale}
				title="Zoom Out"
			>
				<span class="flex items-center gap-2">
					<ZoomOutIcon class="h-5 w-5" />
					{#if isExpanded}<span class="text-xs">Zoom Out</span>{/if}
				</span>
			</button>
		</div>

		<div class="bg-text/20 my-1 h-px w-full"></div>

		<button
			class="{buttonClass} {isExpanded ? 'w-full justify-start' : ''}"
			onclick={onFitHeight}
			title="Fit Height"
		>
			<span class="flex items-center gap-2">
				<FitPageIcon class="h-5 w-5" />
				{#if isExpanded}<span class="text-xs">Fit Height</span>{/if}
			</span>
		</button>

		<div class="bg-text/20 my-1 h-px w-full"></div>

		{#if numPages > 1}
			<!-- Page Navigation -->
			<div class="flex {isExpanded ? 'w-full justify-between' : 'flex-col'} items-center gap-1">
				<button
					class="{buttonClass} {isExpanded ? '' : ''}"
					onclick={onPrevPage}
					disabled={pageNumber <= 1}
					title="Previous Page"
				>
					<ChevronUpIcon class="h-5 w-5" />
				</button>
				<span class="text-text/70 text-xs {isExpanded ? 'mx-2' : ''}">{pageNumber}/{numPages}</span>
				<button
					class="{buttonClass} {isExpanded ? '' : ''}"
					onclick={onNextPage}
					disabled={pageNumber >= numPages}
					title="Next Page"
				>
					<ChevronDownIcon class="h-5 w-5" />
				</button>
			</div>

			<div class="bg-text/20 my-1 h-px w-full"></div>
		{/if}

		<!-- View Mode Selector (admin/owner only) -->
		<ViewModeSelector {isExpanded} />

		<div class="bg-text/20 my-1 h-px w-full"></div>

		<!-- Other Cursors Toggle -->
		<button
			class="{documentStore.showCursors ? activeButtonClass : buttonClass} {isExpanded
				? 'w-full justify-start'
				: ''}"
			onclick={() => (documentStore.showCursors = !documentStore.showCursors)}
			title={documentStore.showCursors ? 'Hide other cursors' : 'Show other cursors'}
		>
			<span class="flex items-center gap-2">
				<CursorIcon class="h-5 w-5" />
				{#if isExpanded}<span class="text-xs"
						>{documentStore.showCursors ? 'Cursors On' : 'Cursors Off'}</span
					>{/if}
			</span>
		</button>

		<div class="bg-text/20 my-1 h-px w-full"></div>

		{#snippet userFilterItem(filter: FilterState<'author'>, compact: boolean)}
			{@const isSessionUser = filter.id === sessionStore.currentUser?.id}
			<div class="flex items-center gap-2">
				{#if isSessionUser}
					<PersonIcon class="text-text/70 h-7 w-7 shrink-0 rounded-full" />
				{:else}
					<div
						class="text-text flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[11px] font-medium {getUserColor(
							filter.id
						)}"
					>
						{getInitials(filter.data.username)}
					</div>
				{/if}
				{#if !compact}
					<span class="text-text/70 truncate text-xs"
						>{filter.data.username} {isSessionUser ? '(You)' : ''}</span
					>
				{/if}
			</div>
		{/snippet}

		<div class="flex items-center justify-between w-full gap-2 p-1">
			<p class="text-text/80">Filters</p>
			{#if anyFilterActive}
				<button
					onclick={() => {
						documentStore.filters.clear();
					}}
					title="Clear All Filters"
					class="cursor-pointer hover:scale-110"
					in:scale
					out:scale
				>
					<ClearFilterIcon class="text-text/50 hover:text-text/70 h-5 w-5" />
				</button>
			{/if}
		</div>

		<!-- Active Users -->
		<FilterList
			label="Active Users"
			placeholderLabel="No other users viewing"
			compact={!isExpanded}
			filters={activeUserFilters}
			item={userFilterItem}
		/>

		<!--Document Authors-->
		<FilterList
			label="Offline Users"
			compact={!isExpanded}
			filters={documentAuthorFilters}
			item={userFilterItem}
		/>

		<!-- Tag Filters -->
		<FilterList label="Tags" compact={!isExpanded} filters={tagFilters}>
			{#snippet item(filter, compact)}
				<div class="flex items-center gap-2">
					<span
						class="text-text/70 h-4 w-4 truncate rounded-full text-xs"
						style="background-color: {filter.data.color}"
					></span>
					<p class="text-md whitespace-nowrap truncate">
						{compact ? filter.data.label.slice(0, 2).toUpperCase() : filter.data.label}
					</p>
				</div>
			{/snippet}
		</FilterList>
	</div>
</div>
