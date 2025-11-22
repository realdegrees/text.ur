<script lang="ts">
	import ZoomInIcon from '~icons/material-symbols/zoom-in';
	import ZoomOutIcon from '~icons/material-symbols/zoom-out';
	import FitPageIcon from '~icons/material-symbols/fit-page';
	import ChevronUpIcon from '~icons/material-symbols/keyboard-arrow-up';
	import ChevronDownIcon from '~icons/material-symbols/keyboard-arrow-down';

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
</script>

<div class="flex w-12 shrink-0 flex-col items-center gap-1 border-r border-text/10 bg-inset py-3">
	<!-- Zoom Controls -->
	<button
		class="rounded p-2 text-text/70 transition-colors hover:bg-text/10 hover:text-text disabled:opacity-30 disabled:hover:bg-transparent"
		onclick={onZoomIn}
		disabled={scale >= maxScale}
		title="Zoom In"
	>
		<ZoomInIcon class="h-5 w-5" />
	</button>
	<button
		class="rounded p-2 text-text/70 transition-colors hover:bg-text/10 hover:text-text disabled:opacity-30 disabled:hover:bg-transparent"
		onclick={onZoomOut}
		disabled={scale <= minScale}
		title="Zoom Out"
	>
		<ZoomOutIcon class="h-5 w-5" />
	</button>

	<div class="my-1 h-px w-6 bg-text/20"></div>

	<button
		class="rounded p-2 text-text/70 transition-colors hover:bg-text/10 hover:text-text"
		onclick={onFitHeight}
		title="Fit Height"
	>
		<FitPageIcon class="h-5 w-5" />
	</button>

	<div class="my-1 h-px w-6 bg-text/20"></div>

	<!-- Page Navigation -->
	<button
		class="rounded p-2 text-text/70 transition-colors hover:bg-text/10 hover:text-text disabled:opacity-30 disabled:hover:bg-transparent"
		onclick={onPrevPage}
		disabled={pageNumber <= 1}
		title="Previous Page"
	>
		<ChevronUpIcon class="h-5 w-5" />
	</button>
	<span class="text-xs text-text/70">{pageNumber}/{numPages}</span>
	<button
		class="rounded p-2 text-text/70 transition-colors hover:bg-text/10 hover:text-text disabled:opacity-30 disabled:hover:bg-transparent"
		onclick={onNextPage}
		disabled={pageNumber >= numPages}
		title="Next Page"
	>
		<ChevronDownIcon class="h-5 w-5" />
	</button>
</div>
