<script lang="ts">
	import type { PDFSlick } from '@pdfslick/core';
	import { onDestroy, onMount } from 'svelte';
	import '@pdfslick/core/dist/pdf_viewer.css';
	import AnnotationLayer from './AnnotationLayer.svelte';
	import TextSelectionHandler from './TextSelectionHandler.svelte';
	import CommentSidebar from './CommentSidebar.svelte';
	import PdfControls from './PdfControls.svelte';
	import UserCursors from './UserCursors.svelte';
	import { PDF_ZOOM_STEP, PDF_MIN_SCALE } from './constants';

	interface Props {
		document: ArrayBuffer;
	}

	let { document: pdfData }: Props = $props();

	let container: HTMLDivElement | null = $state(null);
	let pdfAreaWrapper: HTMLDivElement | null = $state(null);
	let sidebarContainer: HTMLDivElement | null = $state(null);
	let pdfSlick: PDFSlick | null = $state(null);
	let unsubscribe: (() => void) | null = $state(null);

	let pageNumber = $state(1);
	let numPages = $state(0);
	let scale = $state(1);
	let scrollTop = $state(0);
	let pdfWidth = $state(0);
	let basePageWidth = $state(0);
	let maxAvailableWidth = $state(0);

	const updatePdfWidth = () => {
		if (!container) return;
		const page = container.querySelector('.page') as HTMLElement | null;
		if (page) {
			const pageRect = page.getBoundingClientRect();
			pdfWidth = pageRect.width + 16;

			if (scale > 0) {
				basePageWidth = page.clientWidth / scale;
			}
		}
	};

	const captureMaxAvailableWidth = () => {
		if (!pdfAreaWrapper) return;
		const parent = pdfAreaWrapper.parentElement;
		if (parent) {
			const available = parent.clientWidth - 48 - 288;
			if (available > maxAvailableWidth) {
				maxAvailableWidth = available;
			}
		}
	};

	let maxScale = $derived(
		basePageWidth > 0 && maxAvailableWidth > 0 ? (maxAvailableWidth - 16) / basePageWidth : 10
	);

	const initialize = async () => {
		if (!container) return;

		const { create, PDFSlick } = await import('@pdfslick/core');
		const store = create();

		pdfSlick = new PDFSlick({
			container,
			store,
			options: {
				scaleValue: 'page-height'
			}
		});

		pdfSlick.loadDocument(pdfData);
		store.setState({ pdfSlick });

		unsubscribe = store.subscribe((s) => {
			pageNumber = s.pageNumber;
			numPages = s.numPages;

			// Clamp incoming scale to respect the configured min/max values.
			// This prevents modes like `page-height` from producing a scale
			// that is larger than what's available in the UI.
			const incomingScale = s.scale ?? 1;
			const clampedScale = Math.min(Math.max(incomingScale, PDF_MIN_SCALE), maxScale);

			// If the store attempted to set a scale above the computed max, force
			// the pdf viewer to use the clamped value so UI and viewer stay in sync.
			if (incomingScale !== clampedScale && pdfSlick) {
				pdfSlick.currentScale = clampedScale;
			}

			scale = clampedScale;
			requestAnimationFrame(() => {
				updatePdfWidth();
				captureMaxAvailableWidth();
			});
		});
	};

	const handleScroll = (e: Event) => {
		const target = e.target as HTMLElement;
		scrollTop = target.scrollTop;
	};

	// Forward wheel events from comments sidebar to PDF container
	const handleCommentsWheel = (e: WheelEvent) => {
		if (!container) return;
		e.preventDefault();
		if (e.ctrlKey) {
			// Ctrl+wheel zooms the PDF
			if (e.deltaY < 0) {
				zoomIn();
			} else {
				zoomOut();
			}
		} else {
			container.scrollTop += e.deltaY;
		}
	};

	// Handle Ctrl+wheel zoom on PDF area
	const handlePdfWheel = (e: WheelEvent) => {
		if (e.ctrlKey) {
			e.preventDefault();
			if (e.deltaY < 0) {
				zoomIn();
			} else {
				zoomOut();
			}
		}
	};

	const zoomIn = () => {
		if (!pdfSlick) return;
		pdfSlick.currentScale = scale + PDF_ZOOM_STEP;
	};

	const zoomOut = () => {
		if (!pdfSlick) return;
		pdfSlick.currentScale = scale - PDF_ZOOM_STEP;
	};

	const fitHeight = () => {
		if (pdfSlick) pdfSlick.currentScaleValue = 'page-height';
	};

	const prevPage = () => pdfSlick?.gotoPage(Math.max(pageNumber - 1, 1));
	const nextPage = () => pdfSlick?.gotoPage(Math.min(pageNumber + 1, numPages));

	$effect(() => {
		if (!pdfAreaWrapper?.parentElement) return;
		const parent = pdfAreaWrapper.parentElement;
		const resizeObserver = new ResizeObserver(() => {
			const available = parent.clientWidth - 48 - 288;
			maxAvailableWidth = available;
		});
		resizeObserver.observe(parent);
		return () => resizeObserver.disconnect();
	});

	onMount(initialize);
	onDestroy(() => unsubscribe?.());
</script>

<div class="pdf-viewer-container flex h-full w-full bg-background">
	<PdfControls
		{scale}
		minScale={PDF_MIN_SCALE}
		{maxScale}
		{pageNumber}
		{numPages}
		onZoomIn={zoomIn}
		onZoomOut={zoomOut}
		onFitHeight={fitHeight}
		onPrevPage={prevPage}
		onNextPage={nextPage}
	/>

	<!-- PDF Viewer Area - shrinks to fit content when zoomed out -->
	<div
		class="relative h-full overflow-hidden bg-text/5 transition-[width] duration-150"
		style="width: {pdfWidth > 0 ? `${pdfWidth}px` : '100%'}; max-width: 100%;"
		bind:this={pdfAreaWrapper}
	>
		<div
			id="viewerContainer"
			class="pdfSlickContainer scrollbar-none absolute inset-0 overflow-x-hidden overflow-y-scroll"
			bind:this={container}
			onscroll={handleScroll}
			onwheel={handlePdfWheel}
		>
			<div id="viewer" class="pdfSlickViewer pdfViewer"></div>
		</div>

		<!-- Annotation highlights are rendered into the PDF pages -->
		<AnnotationLayer viewerContainer={container} {scale} />

		<!-- Text selection handler for creating new annotations -->
		<TextSelectionHandler viewerContainer={container} />

		<!-- Other users' cursors -->
		<UserCursors viewerContainer={container} />
	</div>

	<!-- Right Sidebar - Comments (expands to fill remaining space) -->
	<div
		class="relative min-w-72 flex-1 overflow-hidden border-l border-text/10 bg-inset"
		onwheel={handleCommentsWheel}
		role="complementary"
		bind:this={sidebarContainer}
	>
		<CommentSidebar viewerContainer={container} {sidebarContainer} {scale} {scrollTop} />
	</div>
</div>

<style>
	/* Override PDF.js CSS variables to reduce spacing */
	:global(.pdf-viewer-container) {
		--page-margin: 4px 0;
		--page-border: none;
		--pdfViewer-padding-bottom: 0;
	}

	:global(.pdf-viewer-container .pdfViewer .page) {
		margin: var(--page-margin);
		border: var(--page-border);
	}

	:global(.pdf-viewer-container .pdfViewer) {
		padding: 4px 8px;
	}

	/* Improve clarity on high DPI displays by preferring crisp edges for
	   canvas renderings when scaling occurs. This reduces perceived blur
	   when the browser performs CSS scaling or when devicePixelRatio > 1. */
	:global(.pdf-viewer-container .pdfViewer .canvasWrapper canvas) {
		/* Use the best-available browser rendering hints for crisp text */
		image-rendering: -webkit-optimize-contrast;
		image-rendering: crisp-edges;
		image-rendering: pixelated;
	}
</style>
