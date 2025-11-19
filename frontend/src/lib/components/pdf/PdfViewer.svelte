<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { browser } from '$app/environment';
	import type { CommentRead } from '$api/types';
	import type { Annotation, TextLayerItem } from '$types/pdf';
	import { mergeHighlightBoxes } from '$lib/util/pdfUtils';
	import { commentStore } from '$lib/stores/commentStore';
	import TextLayer from './TextLayer.svelte';
	import HighlightLayer from './HighlightLayer.svelte';

	interface Props {
		pdfSource: Blob;
		comments: CommentRead[];
		scale?: number;
		highlightColor?: string;
		hoveredCommentId?: number | null;
		focusedCommentId?: number | null;
		totalPages?: number;
		currentPage?: number;
		pdfContainerRef?: HTMLDivElement | null;
		onPageDataUpdate?: (
			pageData: Array<{ pageNumber: number; width: number; height: number }>
		) => void;
	}

	let {
		pdfSource,
		comments = [],
		scale = $bindable(1.5),
		highlightColor = $bindable('#FFFF00'),
		hoveredCommentId = $bindable(null),
		focusedCommentId = $bindable(null),
		totalPages = $bindable(0),
		currentPage = $bindable(1),
		pdfContainerRef = $bindable(null),
		onPageDataUpdate = () => {}
	}: Props = $props();

	interface TextItem {
		str: string;
		transform: number[];
		width: number;
		height: number;
		dir: string;
		fontName: string;
	}

	type PageStatus = 'placeholder' | 'rendering' | 'ready';

	interface PageData {
		pageNumber: number;
		status: PageStatus;
		canvas: HTMLCanvasElement | null;
		textLayerRef: HTMLDivElement | null;
		textLayerItems: TextLayerItem[];
		width: number;
		height: number;
		renderTask: any | null; // Store the render task so we can cancel it
	}

	// State
	let pdfDocument: any = $state(null);
	let isLoading: boolean = $state(true);
	let error: string = $state('');
	let pages: PageData[] = $state([]);
	let pdfjsLib: any = $state(null);

	// PDF.js worker setup
	onMount(async () => {
		if (browser) {
			pdfjsLib = await import('pdfjs-dist');
			pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
				'pdfjs-dist/build/pdf.worker.min.mjs',
				import.meta.url
			).toString();
			await loadPDF();
		}
	});

	// Load PDF from Blob
	async function loadPDF() {
		if (!pdfjsLib) {
			console.log('PdfViewer: pdfjsLib not loaded yet');
			return;
		}

		try {
			console.log('PdfViewer: Starting PDF load');
			isLoading = true;
			const arrayBuffer = await pdfSource.arrayBuffer();
			const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
			pdfDocument = await loadingTask.promise;
			totalPages = pdfDocument.numPages;
			console.log(`PdfViewer: PDF loaded, ${totalPages} pages`);

			// Initialize all pages with placeholder status
			pages = Array.from({ length: totalPages }, (_, i) => ({
				pageNumber: i + 1,
				status: 'placeholder' as PageStatus,
				canvas: null,
				textLayerRef: null,
				textLayerItems: [],
				width: 0,
				height: 0,
				renderTask: null
			}));

			isLoading = false;

			// Wait for DOM to be ready
			await new Promise((resolve) => setTimeout(resolve, 100));

			// Start progressive loading: render first page immediately, then queue others
			console.log('PdfViewer: Starting page rendering');
			await renderPageProgressive(0);
			queueRemainingPages();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load PDF';
			console.error('PDF loading error:', err);
			isLoading = false;
		}
	}

	// Render a specific page progressively
	async function renderPageProgressive(pageIndex: number) {
		if (!pdfDocument || !pdfjsLib) return;

		const pageData = pages[pageIndex];
		if (!pageData) return;

		// Skip if already ready or currently rendering
		if (pageData.status === 'ready' || pageData.status === 'rendering') return;

		// Cancel any existing render task for this page
		if (pageData.renderTask) {
			console.log(`PdfViewer: Cancelling existing render task for page ${pageIndex + 1}`);
			try {
				pageData.renderTask.cancel();
			} catch {
				// Ignore cancellation errors
			}
			pageData.renderTask = null;
		}

		console.log(`PdfViewer: Rendering page ${pageIndex + 1}`);

		// Wait for canvas to be available
		let attempts = 0;
		while (!pageData.canvas && attempts < 30) {
			await new Promise((resolve) => setTimeout(resolve, 50));
			attempts++;
		}

		if (!pageData.canvas) {
			console.warn(`Canvas for page ${pageIndex + 1} not available after ${attempts} attempts`);
			return;
		}

		console.log(`PdfViewer: Canvas ready for page ${pageIndex + 1} after ${attempts} attempts`);

		try {
			pageData.status = 'rendering';

			const page = await pdfDocument.getPage(pageData.pageNumber);

			// Get viewport - PDF.js will handle rotation automatically
			const viewport = page.getViewport({ scale });

			const canvas = pageData.canvas;
			const context = canvas.getContext('2d', { alpha: false });
			if (!context) return;

			// Set canvas pixel dimensions (not CSS dimensions)
			canvas.width = viewport.width;
			canvas.height = viewport.height;

			// Update page dimensions
			pageData.width = viewport.width;
			pageData.height = viewport.height;

			// Fill with white background
			context.fillStyle = 'white';
			context.fillRect(0, 0, canvas.width, canvas.height);

			// Render PDF page
			pageData.renderTask = page.render({
				canvasContext: context,
				viewport: viewport
			});

			await pageData.renderTask.promise;
			pageData.renderTask = null;

			// Render text layer
			await renderTextLayer(pageIndex, page, viewport);

			pageData.status = 'ready';
			console.log(
				`PdfViewer: Page ${pageIndex + 1} rendered successfully at ${viewport.width}x${viewport.height}, scale=${scale}`
			);

			// Update page data for parent component
			updatePageDataArray();
		} catch (err: any) {
			if (err?.name !== 'RenderingCancelledException') {
				console.error(`Page ${pageIndex + 1} rendering error:`, err);
			}
			pageData.renderTask = null;
			pageData.status = 'placeholder';
		}
	}

	// Queue remaining pages for async rendering
	function queueRemainingPages() {
		setTimeout(async () => {
			for (let i = 1; i < totalPages; i++) {
				await renderPageProgressive(i);
				// Small delay between pages to keep UI responsive
				await new Promise((resolve) => setTimeout(resolve, 50));
			}
		}, 100);
	}

	// Render text layer for selection
	async function renderTextLayer(pageIndex: number, page: any, viewport: any) {
		const pageData = pages[pageIndex];
		if (!pageData) return;

		try {
			const textContent = await page.getTextContent();
			const items: TextLayerItem[] = [];

			textContent.items.forEach((item: TextItem, index: number) => {
				const tx = pdfjsLib.Util.transform(viewport.transform, item.transform);
				const style = textContent.styles?.[item.fontName];
				const angle = Math.atan2(tx[1], tx[0]);
				const fontHeight = Math.hypot(tx[2], tx[3]);
				const fontAscent = style?.ascent || 0.8;
				const left = tx[4];
				const top = tx[5] - fontHeight * fontAscent;

				items.push({
					id: `text-${pageData.pageNumber}-${index}`,
					text: item.str,
					left,
					top,
					fontSize: fontHeight,
					fontFamily: style?.fontFamily || 'sans-serif',
					angle
				});
			});

			pageData.textLayerItems = items;
		} catch (err) {
			console.error('Text layer rendering error:', err);
		}
	}

	// Handle text selection and highlight creation
	async function handleTextSelection(pageIndex: number) {
		const selection = window.getSelection();
		if (!selection || selection.isCollapsed || !selection.rangeCount) return;

		const selectedText = selection.toString().trim();
		if (selectedText.length === 0) return;

		const pageData = pages[pageIndex];
		if (!pageData?.textLayerRef || pageData.width === 0 || pageData.height === 0) return;

		const textLayerRect = pageData.textLayerRef.getBoundingClientRect();
		if (!textLayerRect) return;

		// Get all client rects for multi-line selections
		const range = selection.getRangeAt(0);
		const clientRects = range.getClientRects();

		// Convert to relative positions
		const rawBoxes = Array.from(clientRects)
			.filter((rect) => rect.width > 0 && rect.height > 0)
			.map((rect) => ({
				x: rect.left - textLayerRect.left,
				y: rect.top - textLayerRect.top,
				width: rect.width,
				height: rect.height
			}));

		if (rawBoxes.length === 0) return;

		// Merge overlapping boxes
		const mergedBoxes = mergeHighlightBoxes(rawBoxes);

		// Normalize to 0-1 range
		const normalizedBoxes = mergedBoxes.map((box) => ({
			x: box.x / pageData.width,
			y: box.y / pageData.height,
			width: box.width / pageData.width,
			height: box.height / pageData.height
		}));

		const annotation: Annotation = {
			pageNumber: pageData.pageNumber,
			text: selectedText,
			boundingBoxes: normalizedBoxes,
			color: highlightColor,
			timestamp: Date.now()
		};

		// Create comment with annotation directly via store
		await commentStore.create({ annotation });

		// Clear selection
		window.getSelection()?.removeAllRanges();
	}

	// Handle mouse move for hover detection
	function handleMouseMove(event: MouseEvent, pageIndex: number) {
		const pageData = pages[pageIndex];
		if (!pageData?.textLayerRef || pageData.status !== 'ready') return;

		const rect = pageData.textLayerRef.getBoundingClientRect();
		const localMouseX = event.clientX - rect.left;
		const localMouseY = event.clientY - rect.top;

		const pageComments = comments.filter((c) => {
			const annotation = c.annotation as unknown as Annotation;
			return annotation?.pageNumber === pageData.pageNumber;
		});

		let foundHover = false;
		for (const comment of pageComments) {
			const annotation = comment.annotation as unknown as Annotation;
			const scaledBoxes = annotation.boundingBoxes.map((box) => ({
				x: box.x * pageData.width,
				y: box.y * pageData.height,
				width: box.width * pageData.width,
				height: box.height * pageData.height
			}));

			const margin = 3;
			const isOver = scaledBoxes.some(
				(box) =>
					localMouseX >= box.x - margin &&
					localMouseX <= box.x + box.width + margin &&
					localMouseY >= box.y - margin &&
					localMouseY <= box.y + box.height + margin
			);

			if (isOver) {
				hoveredCommentId = comment.id;
				foundHover = true;
				break;
			}
		}

		if (!foundHover) {
			hoveredCommentId = null;
		}
	}

	// Update page data array for parent
	function updatePageDataArray() {
		const data = pages
			.filter((p) => p.width > 0 && p.height > 0)
			.map((p) => ({
				pageNumber: p.pageNumber,
				width: p.width,
				height: p.height
			}));
		onPageDataUpdate(data);
	}

	// Re-render all pages when scale changes
	let previousScale = $state(0);
	let scaleInitialized = $state(false);
	$effect(() => {
		// Initialize previous scale on first run
		if (!scaleInitialized) {
			previousScale = scale;
			scaleInitialized = true;
			return;
		}

		// Only re-render if scale actually changed and we have a document
		if (pdfDocument && pages.length > 0 && scale !== previousScale) {
			console.log(
				`PdfViewer: Scale changed from ${previousScale} to ${scale}, re-rendering all pages`
			);
			previousScale = scale;

			// Re-render all loaded pages
			for (let i = 0; i < pages.length; i++) {
				if (pages[i].status === 'ready') {
					// Mark for re-render without changing status immediately
					// This will trigger the render cancellation in renderPageProgressive
					setTimeout(() => renderPageProgressive(i), 10);
				}
			}
		}
	});

	// Watch for PDF source changes
	let previousPdfSource: Blob | null = null;
	$effect(() => {
		if (pdfSource && pdfjsLib && pdfSource !== previousPdfSource) {
			console.log('PdfViewer: PDF source changed, loading new PDF');
			previousPdfSource = pdfSource;
			loadPDF();
		}
	});

	// Cleanup
	onDestroy(() => {
		if (pdfDocument) {
			pdfDocument.destroy();
		}
	});
</script>

<div
	bind:this={pdfContainerRef}
	class="pdf-container flex flex-col items-center gap-4 bg-gray-100 p-4"
>
	{#if isLoading}
		<div class="flex items-center justify-center py-20">
			<div class="text-center">
				<div
					class="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-b-2 border-blue-600"
				></div>
				<p class="text-gray-600">Loading PDF...</p>
			</div>
		</div>
	{:else if error}
		<div class="flex items-center justify-center py-20">
			<div class="max-w-md rounded-lg bg-red-50 p-6 text-center">
				<svg
					class="mx-auto mb-4 h-16 w-16 text-red-500"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
					/>
				</svg>
				<h3 class="mb-2 text-lg font-semibold text-gray-900">Error Loading PDF</h3>
				<p class="text-gray-600">{error}</p>
			</div>
		</div>
	{:else if pdfDocument}
		{#each pages as pageData (pageData.pageNumber)}
			<div class="page-wrapper relative bg-white shadow-lg" data-page-number={pageData.pageNumber}>
				<!-- Canvas for PDF rendering (always rendered) -->
				<canvas
					bind:this={pageData.canvas}
					class="block"
					style="display: block;"
					class:opacity-0={pageData.status === 'placeholder' || pageData.status === 'rendering'}
				></canvas>

				<!-- Loading placeholder overlay -->
				{#if pageData.status === 'placeholder' || pageData.status === 'rendering'}
					<div
						class="absolute inset-0 flex items-center justify-center bg-gray-200"
						style="min-width: 612px; min-height: 792px;"
					>
						<div class="text-center">
							<div
								class="mx-auto mb-2 h-8 w-8 animate-spin rounded-full border-b-2 border-gray-400"
							></div>
							<p class="text-sm text-gray-500">Loading page {pageData.pageNumber}...</p>
						</div>
						<!-- Shimmer effect -->
						<div class="shimmer absolute inset-0 -z-10"></div>
					</div>
				{/if}

				{#if pageData.status === 'ready'}
					<!-- Text Layer (for selection) -->
					<TextLayer
						bind:textLayerRef={pageData.textLayerRef}
						textLayerItems={pageData.textLayerItems}
						width={pageData.width}
						height={pageData.height}
						onTextSelection={() => handleTextSelection(pages.indexOf(pageData))}
						onMouseMove={(e) => handleMouseMove(e, pages.indexOf(pageData))}
						onMouseLeave={() => (hoveredCommentId = null)}
					/>

					<!-- Highlight Layer -->
					<HighlightLayer
						{comments}
						pageNumber={pageData.pageNumber}
						width={pageData.width}
						height={pageData.height}
						{hoveredCommentId}
						{focusedCommentId}
					/>
				{/if}
			</div>
		{/each}
	{/if}
</div>

<style>
	.page-wrapper {
		position: relative;
	}

	.shimmer {
		background: linear-gradient(
			90deg,
			rgba(255, 255, 255, 0) 0%,
			rgba(255, 255, 255, 0.3) 50%,
			rgba(255, 255, 255, 0) 100%
		);
		background-size: 200% 100%;
		animation: shimmer 1.5s infinite;
	}

	@keyframes shimmer {
		0% {
			background-position: -200% 0;
		}
		100% {
			background-position: 200% 0;
		}
	}
</style>
