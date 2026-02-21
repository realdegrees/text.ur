<script lang="ts">
	import LL from '$i18n/i18n-svelte';
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
	import DocumentTutorial from './DocumentTutorial.svelte';
	import { documentStore, type FilterState } from '$lib/runes/document.svelte.js';
	import { documentWebSocket } from '$lib/stores/documentWebSocket.svelte';
	import { sessionStore } from '$lib/runes/session.svelte';
	import PersonIcon from '~icons/material-symbols/person';
	import ClearFilterIcon from '~icons/mdi/filter-remove-outline';
	import { scale } from 'svelte/transition';
	import TagIcon from '~icons/mdi/tag-outline';
	import ActiveUsersIcon from '~icons/heroicons-outline/status-online';
	import OfflineIcon from '~icons/oui/offline';
	import PinIcon from '~icons/mdi/pin';
	import PinOutlineIcon from '~icons/mdi/pin-outline';
	import EyeIcon from '~icons/mdi/eye';
	import EyeOffIcon from '~icons/mdi/eye-off';

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
		isMobile?: boolean;
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
		onNextPage,
		isMobile = false
	}: Props = $props();

	let isExpanded = $state(!isMobile); // Collapsed by default on mobile

	const buttonClass =
		'rounded p-2 text-text/70 transition-colors hover:bg-text/10 hover:text-text disabled:opacity-30 disabled:hover:bg-transparent';
	const activeButtonClass =
		'rounded p-2 text-primary bg-primary/10 transition-colors hover:bg-primary/20';

	const iconSizeClass = 'h-5 w-5';

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

	const globalPinStatus = $derived.by(() => {
		return documentStore.getGlobalPinStatus();
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
	class="no-scrollbar flex shrink-0 flex-col overflow-x-hidden overflow-y-auto border-r border-text/10 bg-inset transition-all duration-200 {isExpanded
		? 'w-48'
		: 'w-12'} {isMobile ? 'absolute top-0 left-0 z-40' : ''}"
	style={isMobile ? 'bottom: var(--mobile-comment-panel-height, 0px);' : ''}
>
	<!-- Expand/Collapse Button -->
	<button
		class="flex items-center justify-center gap-2 border-b border-text/10 p-2 text-text/50 transition-colors hover:bg-text/5 hover:text-text/70"
		onclick={() => (isExpanded = !isExpanded)}
		title={isExpanded ? $LL.collapse() : $LL.pdf.expand()}
	>
		{#if isExpanded}
			<CollapseIcon class={iconSizeClass} />
			<span class="text-xs">{$LL.collapse()}</span>
		{:else}
			<ExpandIcon class={iconSizeClass} />
		{/if}
	</button>

	<div class="flex flex-col items-center gap-1 py-3 {isExpanded ? 'px-2' : ''}">
		<!-- Zoom Controls -->
		{#if !isMobile}
			<div class="flex {isExpanded ? 'w-full justify-between' : 'flex-col'} items-center gap-1">
				<button
					class="{buttonClass} {isExpanded ? 'flex-1' : ''}"
					onclick={onZoomIn}
					disabled={documentStore.documentScale >= maxScale}
				title={$LL.pdf.zoomIn()}
			>
				<span class="flex items-center gap-2">
					<ZoomInIcon class={iconSizeClass} />
					{#if isExpanded}<span class="text-xs">{$LL.pdf.zoomIn()}</span>{/if}
					</span>
				</button>
				<button
					class="{buttonClass} {isExpanded ? 'flex-1' : ''}"
					onclick={onZoomOut}
					disabled={documentStore.documentScale <= minScale}
				title={$LL.pdf.zoomOut()}
			>
				<span class="flex items-center gap-2">
					<ZoomOutIcon class={iconSizeClass} />
					{#if isExpanded}<span class="text-xs">{$LL.pdf.zoomOut()}</span>{/if}
					</span>
				</button>
			</div>

			<div class="my-1 h-px w-full bg-text/20"></div>

			<button
				class="{buttonClass} {isExpanded ? 'w-full justify-start' : ''}"
				onclick={onFitHeight}
			title={$LL.pdf.fitHeight()}
		>
			<span class="flex items-center gap-2">
				<FitPageIcon class={iconSizeClass} />
				{#if isExpanded}<span class="text-xs">{$LL.pdf.fitHeight()}</span>{/if}
				</span>
			</button>

			<div class="my-1 h-px w-full bg-text/20"></div>
		{/if}

		{#if numPages > 1}
			<!-- Page Navigation -->
			<div class="flex {isExpanded ? 'w-full justify-between' : 'flex-col'} items-center gap-1">
				<button
					class="{buttonClass} {isExpanded ? '' : ''}"
					onclick={onPrevPage}
					disabled={pageNumber <= 1}
					title={$LL.pdf.previousPage()}
				>
					<ChevronUpIcon class={iconSizeClass} />
				</button>
				<span class="text-xs text-text/70 {isExpanded ? 'mx-2' : ''}">{pageNumber}/{numPages}</span>
				<button
					class="{buttonClass} {isExpanded ? '' : ''}"
					onclick={onNextPage}
					disabled={pageNumber >= numPages}
					title={$LL.pdf.nextPage()}
				>
					<ChevronDownIcon class={iconSizeClass} />
				</button>
			</div>

			<div class="my-1 h-px w-full bg-text/20"></div>
		{/if}

		<!-- View Mode Selector (admin/owner only) -->
		<ViewModeSelector {isExpanded} />

		<div class="my-1 h-px w-full bg-text/20"></div>

		<!-- Cursor Controls -->
		<div class="flex flex-col {isExpanded ? 'w-full justify-between' : ''} items-center gap-1">
			<!-- Share My Cursor -->
			<button
				class="w-full {documentStore.shareCursor ? activeButtonClass : buttonClass} {isExpanded
					? 'flex-1'
					: ''}"
				onclick={() => {
					documentStore.shareCursor = !documentStore.shareCursor;
					if (!documentStore.shareCursor) {
						documentWebSocket.forceHideCursor();
					}
				}}
			>
				<span class="flex items-center justify-center gap-2">
					<CursorIcon class={iconSizeClass} />
					{#if isExpanded}<span class="text-xs">{$LL.pdf.shareCursor()}</span>{/if}
				</span>
			</button>

			<!-- Show Other Cursors -->
			<button
				class="w-full {documentStore.showCursors ? activeButtonClass : buttonClass} {isExpanded
					? 'flex-1'
					: ''}"
				onclick={() => (documentStore.showCursors = !documentStore.showCursors)}
			>
				<span class="flex items-center justify-center gap-2">
					{#if documentStore.showCursors}
						<EyeIcon class={iconSizeClass} />
					{:else}
						<EyeOffIcon class={iconSizeClass} />
					{/if}
					{#if isExpanded}<span class="text-xs">{$LL.pdf.showOtherCursors()}</span>{/if}
				</span>
			</button>
		</div>

		<div class="my-1 h-px w-full bg-text/20"></div>

		{#snippet userFilterItem(filter: FilterState<'author'>, compact: boolean)}
			{@const isSessionUser = filter.id === sessionStore.currentUser?.id}
			<div class="flex min-w-0 items-center gap-2" title={filter.data.username}>
				{#if isSessionUser}
					<PersonIcon class="text-text/70 {iconSizeClass} shrink-0 rounded-full" />
				{:else}
					<div
						class="flex text-text {iconSizeClass} shrink-0 items-center justify-center rounded-full text-[11px] font-medium {getUserColor(
							filter.id
						)}"
					>
						{getInitials(filter.data.username)}
					</div>
				{/if}
				{#if !compact}
					<span class="min-w-0 truncate text-xs text-text/70"
						>{filter.data.username} {isSessionUser ? $LL.pdf.you() : ''}</span
					>
				{/if}
			</div>
		{/snippet}

		<div class="flex w-full items-center {isExpanded ? 'justify-between' : 'justify-center'} gap-2">
			{#if isExpanded}
				<p class="font-medium text-text/80">{$LL.pdf.filtersAndPins()}</p>
			{/if}
			<div class="flex items-center gap-1">
				<button
					onclick={() => {
						documentStore.pinAll(!globalPinStatus.anyPinned);
					}}
					title={globalPinStatus.anyPinned ? $LL.pdf.unpinAllComments() : $LL.pdf.pinAllComments()}
					class="cursor-pointer hover:scale-110"
					in:scale
					out:scale
				>
					{#if globalPinStatus.anyPinned}
						<PinIcon class="text-text/50 hover:text-text/70 {iconSizeClass}" />
					{:else}
						<PinOutlineIcon class="text-text/50 hover:text-text/70 {iconSizeClass}" />
					{/if}
				</button>

				{#if anyFilterActive}
					<button
						onclick={() => {
							documentStore.filters.clear();
						}}
						title={$LL.pdf.clearAllFilters()}
						class="cursor-pointer hover:scale-110"
						in:scale
						out:scale
					>
						<ClearFilterIcon class="text-text/50 hover:text-text/70 {iconSizeClass}" />
					</button>
				{/if}
			</div>
		</div>

		<DocumentTutorial {isExpanded} />
		<!-- Active Users -->
		<FilterList
			placeholderLabel={$LL.pdf.noOtherUsers()}
			compact={!isExpanded}
			filters={activeUserFilters}
			item={userFilterItem}
		>
			{#snippet header(compact)}
			<div class="flex items-center gap-2" title={isExpanded ? '' : $LL.pdf.activeUsers()}>
				<ActiveUsersIcon class={iconSizeClass} />
				{#if !compact}
					<span>{$LL.pdf.activeUsers()}</span>
					{/if}
				</div>
			{/snippet}
		</FilterList>

		<!--Document Authors-->
		<FilterList compact={!isExpanded} filters={documentAuthorFilters} item={userFilterItem}>
			{#snippet header(compact)}
			<div class="flex items-center gap-2" title={isExpanded ? '' : $LL.pdf.offlineUsers()}>
				<OfflineIcon class={iconSizeClass} />
				{#if !compact}
					<span>{$LL.pdf.offlineUsers()}</span>
					{/if}
				</div>
			{/snippet}
		</FilterList>

		<!-- Tag Filters -->
		<FilterList compact={!isExpanded} filters={tagFilters}>
			{#snippet header(compact)}
			<div class="flex items-center gap-2" title={isExpanded ? '' : $LL.tags.title()}>
				<TagIcon class={iconSizeClass} />
				{#if !compact}
					<span>{$LL.tags.title()}</span>
					{/if}
				</div>
			{/snippet}
			{#snippet item(filter, compact)}
				<div class="flex min-w-0 items-center gap-2" title={filter.data.label}>
					<p
						class="text-text/70 {iconSizeClass} shrink-0 rounded-md text-xs"
						style="background-color: {filter.data.color}"
					>
						{#if compact}
							{filter.data.label.slice(0, 2).toUpperCase()}
						{/if}
					</p>
					{#if !compact}
						<p class="text-md min-w-0 truncate whitespace-nowrap">
							{filter.data.label}
						</p>
					{/if}
				</div>
			{/snippet}
		</FilterList>
	</div>
</div>
