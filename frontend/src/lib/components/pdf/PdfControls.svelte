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
	import ActiveUsers from './ActiveUsers.svelte';
	import { documentStore } from '$lib/runes/document.svelte.js';
	import { sessionStore } from '$lib/runes/session.svelte.js';

	interface Props {
		scale: number;
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
		scale,
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

	let isExpanded = $state(false);

	// Check if filters should be disabled (restricted mode without view_restricted_comments permission)
	let isRestrictedWithoutPermission = $derived(
		documentStore.loadedDocument?.view_mode === 'restricted' &&
			!sessionStore.validatePermissions(['view_restricted_comments'])
	);

	// Clear filters when view mode changes to restricted and user lacks permission
	$effect(() => {
		if (isRestrictedWithoutPermission && documentStore.hasActiveFilter) {
			documentStore.clearAuthorFilter();
		}
	});

	const buttonClass =
		'rounded p-2 text-text/70 transition-colors hover:bg-text/10 hover:text-text disabled:opacity-30 disabled:hover:bg-transparent';
	const activeButtonClass =
		'rounded p-2 text-primary bg-primary/10 transition-colors hover:bg-primary/20';
</script>

<div
	class="flex shrink-0 flex-col border-r border-text/10 bg-inset transition-all duration-200 {isExpanded
		? 'w-40'
		: 'w-12'}"
>
	<!-- Expand/Collapse Button -->
	<button
		class="flex items-center justify-center gap-2 border-b border-text/10 p-2 text-text/50 transition-colors hover:bg-text/5 hover:text-text/70"
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
				disabled={scale >= maxScale}
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
				disabled={scale <= minScale}
				title="Zoom Out"
			>
				<span class="flex items-center gap-2">
					<ZoomOutIcon class="h-5 w-5" />
					{#if isExpanded}<span class="text-xs">Zoom Out</span>{/if}
				</span>
			</button>
		</div>

		<div class="my-1 h-px w-full bg-text/20"></div>

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

		<div class="my-1 h-px w-full bg-text/20"></div>

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
				<span class="text-xs text-text/70 {isExpanded ? 'mx-2' : ''}">{pageNumber}/{numPages}</span>
				<button
					class="{buttonClass} {isExpanded ? '' : ''}"
					onclick={onNextPage}
					disabled={pageNumber >= numPages}
					title="Next Page"
				>
					<ChevronDownIcon class="h-5 w-5" />
				</button>
			</div>

			<div class="my-1 h-px w-full bg-text/20"></div>
		{/if}

		<!-- View Mode Selector (admin/owner only) -->
		<ViewModeSelector {isExpanded} />

		<div class="my-1 h-px w-full bg-text/20"></div>

		<!-- Other Cursors Toggle -->
		<button
			class="{documentStore.showOtherCursors ? activeButtonClass : buttonClass} {isExpanded
				? 'w-full justify-start'
				: ''}"
			onclick={() => documentStore.setShowOtherCursors(!documentStore.showOtherCursors)}
			title={documentStore.showOtherCursors ? 'Hide other cursors' : 'Show other cursors'}
		>
			<span class="flex items-center gap-2">
				<CursorIcon class="h-5 w-5" />
				{#if isExpanded}<span class="text-xs"
						>{documentStore.showOtherCursors ? 'Cursors On' : 'Cursors Off'}</span
					>{/if}
			</span>
		</button>

		<div class="my-1 h-px w-full bg-text/20"></div>

		<!-- Active Users -->
		<ActiveUsers {isExpanded} />
	</div>
</div>
