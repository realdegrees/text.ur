<script lang="ts">
	interface Props {
		highlightColor?: string;
		commentsCount: number;
		scale?: number;
		currentPage: number;
		totalPages: number;
		onZoomIn?: () => void;
		onZoomOut?: () => void;
		onPagePrev?: () => void;
		onPageNext?: () => void;
	}

	let {
		highlightColor = $bindable('#FFFF00'),
		commentsCount,
		scale = $bindable(1.5),
		currentPage,
		totalPages,
		onZoomIn = () => {},
		onZoomOut = () => {},
		onPagePrev = () => {},
		onPageNext = () => {}
	}: Props = $props();
</script>

<div class="flex flex-col gap-4 p-4">
	<!-- Highlight Color Picker -->
	<section class="rounded-lg border border-text/10 bg-background p-4 shadow-sm">
		<h3 class="mb-3 text-sm font-semibold text-text">Highlight Color</h3>
		<div class="flex flex-col gap-2">
			<input
				id="highlight-color"
				type="color"
				bind:value={highlightColor}
				class="h-12 w-full cursor-pointer rounded-md border border-text/20"
				aria-label="Highlight color picker"
			/>
			<div class="text-xs text-text/60">{highlightColor}</div>
		</div>
	</section>

	<!-- Page Navigation -->
	<section class="rounded-lg border border-text/10 bg-background p-4 shadow-sm">
		<h3 class="mb-3 text-sm font-semibold text-text">Navigation</h3>
		<div class="flex flex-col gap-3">
			<div class="flex items-center justify-between gap-2">
				<button
					onclick={onPagePrev}
					disabled={currentPage <= 1}
					class="flex-1 rounded-md bg-inset px-3 py-2 text-sm font-medium text-text transition-colors hover:bg-text/10 disabled:cursor-not-allowed disabled:opacity-50"
					aria-label="Previous page"
				>
					← Prev
				</button>
				<button
					onclick={onPageNext}
					disabled={currentPage >= totalPages}
					class="flex-1 rounded-md bg-inset px-3 py-2 text-sm font-medium text-text transition-colors hover:bg-text/10 disabled:cursor-not-allowed disabled:opacity-50"
					aria-label="Next page"
				>
					Next →
				</button>
			</div>
			<div class="text-center text-sm text-text/60">
				Page <span class="font-semibold">{currentPage}</span> of
				<span class="font-semibold">{totalPages}</span>
			</div>
		</div>
	</section>

	<!-- Zoom Controls -->
	<section class="rounded-lg border border-text/10 bg-background p-4 shadow-sm">
		<h3 class="mb-3 text-sm font-semibold text-text">Zoom</h3>
		<div class="flex flex-col gap-3">
			<div class="flex items-center justify-between gap-2">
				<button
					onclick={onZoomOut}
					disabled={scale <= 0.5}
					class="flex-1 rounded-md bg-inset px-3 py-2 text-sm font-medium text-text transition-colors hover:bg-text/10 disabled:cursor-not-allowed disabled:opacity-50"
					aria-label="Zoom out"
				>
					−
				</button>
				<button
					onclick={onZoomIn}
					disabled={scale >= 3}
					class="flex-1 rounded-md bg-inset px-3 py-2 text-sm font-medium text-text transition-colors hover:bg-text/10 disabled:cursor-not-allowed disabled:opacity-50"
					aria-label="Zoom in"
				>
					+
				</button>
			</div>
			<div class="text-center text-sm text-text/60">
				<span class="font-semibold">{Math.round(scale * 100)}%</span>
			</div>
		</div>
	</section>

	<!-- Statistics -->
	<section class="rounded-lg border border-text/10 bg-background p-4 shadow-sm">
		<h3 class="mb-3 text-sm font-semibold text-text">Statistics</h3>
		<div class="flex flex-col gap-2">
			<div class="flex items-center justify-between">
				<span class="text-sm text-text/60">Highlights</span>
				<span class="text-lg font-bold text-text">{commentsCount}</span>
			</div>
		</div>
	</section>
</div>
