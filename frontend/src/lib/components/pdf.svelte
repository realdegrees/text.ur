<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { browser } from '$app/environment';
	import type { CommentRead } from '$api/types';

	// Props
	interface Props {
		pdfSource: Blob;
		onAnnotationCreate?: (annotation: Annotation) => void;
		onAnnotationSelect?: (comment: CommentRead) => void;
		comments: CommentRead[];
	}

	let {
		pdfSource,
		onAnnotationCreate = () => {},
		onAnnotationSelect = () => {},
		comments = []
	}: Props = $props();

	interface Annotation {
		pageNumber: number;
		text: string;
		boundingBoxes: {
			x: number;
			y: number;
			width: number;
			height: number;
		}[];
		color: string;
		timestamp: number;
	}

	interface SelectionInfo {
		text: string;
		boundingBox: DOMRect;
		pageNumber: number;
	}

	interface TextItem {
		str: string;
		transform: number[];
		width: number;
		height: number;
		dir: string;
		fontName: string;
	}

	interface TextLayerItem {
		text: string;
		left: number;
		top: number;
		fontSize: number;
		fontFamily: string;
		angle: number;
		id: string;
	}

	// State
	let canvasRef: HTMLCanvasElement | null = $state(null);
	let containerRef: HTMLDivElement | null = $state(null);
	let textLayerRef: HTMLDivElement | null = $state(null);
	let pdfDocument: any = $state(null);
	let currentPage: number = $state(1);
	let totalPages: number = $state(0);
	let scale: number = $state(1.5);
	let isLoading: boolean = $state(true);
	let error: string = $state('');

	// Text layer state
	let textLayerWidth: number = $state(0);
	let textLayerHeight: number = $state(0);
	let textLayerItems: TextLayerItem[] = $state([]);

	// Selection state
	let selectionInfo: SelectionInfo | null = $state(null);

	// Annotations
	let highlightColor: string = $state('#FFFF00');

	// PDF.js library
	let pdfjsLib: any = $state(null);

	// PDF.js worker setup
	onMount(async () => {
		if (browser) {
			pdfjsLib = await import('pdfjs-dist');

			// Set worker source
			pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
				'pdfjs-dist/build/pdf.worker.min.mjs',
				import.meta.url
			).toString();

			await loadPDF();
		}
	});

	// Load PDF from Blob or base64
	async function loadPDF() {
		if (!pdfjsLib) return;

		try {
			isLoading = true;
			const loadingTask = pdfjsLib.getDocument(pdfSource.arrayBuffer());
			pdfDocument = await loadingTask.promise;
			totalPages = pdfDocument.numPages;

			await renderPage(currentPage);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load PDF';
			console.error('PDF loading error:', err);
		} finally {
			isLoading = false;
		}
	}

	// Render a specific page
	async function renderPage(pageNum: number) {
		if (!pdfDocument || !canvasRef || !pdfjsLib) return;

		try {
			const page = await pdfDocument.getPage(pageNum);
			const viewport = page.getViewport({ scale });

			const canvas = canvasRef;
			const context = canvas.getContext('2d');
			if (!context) return;

			// Set canvas dimensions to match viewport
			canvas.height = viewport.height;
			canvas.width = viewport.width;

			// Update text layer dimensions
			textLayerWidth = viewport.width;
			textLayerHeight = viewport.height;

			// Render PDF page
			const renderContext = {
				canvasContext: context,
				viewport: viewport
			};

			await page.render(renderContext).promise;

			// Render text layer for selection
			await renderTextLayer(page, viewport);
		} catch (err) {
			console.error('Page rendering error:', err);
		}
	}

	// Render text layer for text selection
	async function renderTextLayer(page: any, viewport: any) {
		if (!textLayerRef) return;

		try {
			const textContent = await page.getTextContent();

			// Build text layer items array for reactive rendering
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
					id: `text-${currentPage}-${index}`,
					text: item.str,
					left,
					top,
					fontSize: fontHeight,
					fontFamily: style?.fontFamily || 'sans-serif',
					angle
				});
			});

			textLayerItems = items;
		} catch (err) {
			console.error('Text layer rendering error:', err);
		}
	}

	// Handle text selection
	function handleTextSelection() {
		const selection = window.getSelection();
		if (!selection || selection.isCollapsed || !selection.rangeCount) {
			return;
		}

		const selectedText = selection.toString().trim();
		if (selectedText.length === 0) {
			return;
		}

		const range = selection.getRangeAt(0);
		const boundingBox = range.getBoundingClientRect();
		const containerRect = containerRef?.getBoundingClientRect();

		if (!containerRect) return;

		selectionInfo = {
			text: selectedText,
			boundingBox: boundingBox,
			pageNumber: currentPage
		};

		createHighlight();
	}

	// Create highlight annotation
	function createHighlight() {
		if (!selectionInfo) return;

		const selection = window.getSelection();
		if (!selection || !selection.rangeCount) return;

		const textLayerRect = textLayerRef?.getBoundingClientRect();
		if (!textLayerRect) return;

		// Get all client rects for the selection (handles multi-line)
		const range = selection.getRangeAt(0);
		const clientRects = range.getClientRects();

		// Filter out zero-width/height rects and convert to relative positions
		const rawBoxes = Array.from(clientRects)
			.filter((rect) => rect.width > 0 && rect.height > 0)
			.map((rect) => ({
				x: rect.left - textLayerRect.left,
				y: rect.top - textLayerRect.top,
				width: rect.width,
				height: rect.height
			}));

		if (rawBoxes.length === 0) return;

		// Merge overlapping or adjacent boxes on the same line
		const mergedBoxes = mergeHighlightBoxes(rawBoxes);

		// Normalize coordinates (convert to 0-1 range relative to page)
		const normalizedBoxes = mergedBoxes.map((box) => ({
			x: box.x / textLayerWidth,
			y: box.y / textLayerHeight,
			width: box.width / textLayerWidth,
			height: box.height / textLayerHeight
		}));

		const annotation: Annotation = {
			pageNumber: currentPage,
			text: selectionInfo.text,
			boundingBoxes: normalizedBoxes,
			color: highlightColor,
			timestamp: Date.now()
		};

		onAnnotationCreate(annotation);

		// Clear selection
		window.getSelection()?.removeAllRanges();
		selectionInfo = null;
	}

	// Merge overlapping or adjacent highlight boxes
	function mergeHighlightBoxes(
		boxes: { x: number; y: number; width: number; height: number }[],
		overlapThreshold: number = 20
	) {
		if (boxes.length === 0) return [];

		// Sort boxes by y position first, then x position
		const sorted = [...boxes].sort((a, b) => {
			const yDiff = a.y - b.y;
			if (Math.abs(yDiff) > overlapThreshold) return yDiff;
			return a.x - b.x;
		});

		const merged: typeof boxes = [];
		let current = { ...sorted[0] };

		for (let i = 1; i < sorted.length; i++) {
			const box = sorted[i];

			// Check if boxes are on the same line (y positions are close)
			const onSameLine = Math.abs(box.y - current.y) <= overlapThreshold;

			// Check if boxes overlap or are adjacent horizontally
			const xOverlap = box.x <= current.x + current.width + overlapThreshold;

			if (onSameLine && xOverlap) {
				// Merge boxes
				const rightEdge = Math.max(current.x + current.width, box.x + box.width);
				current.width = rightEdge - current.x;
				current.height = Math.max(current.height, box.height);
			} else {
				// Boxes don't overlap, save current and start new
				merged.push(current);
				current = { ...box };
			}
		}

		// Don't forget the last box
		merged.push(current);

		return merged;
	}

	// Page navigation
	function goToPage(pageNum: number) {
		if (pageNum >= 1 && pageNum <= totalPages) {
			currentPage = pageNum;
			renderPage(pageNum);
		}
	}

	function nextPage() {
		goToPage(currentPage + 1);
	}

	function previousPage() {
		goToPage(currentPage - 1);
	}

	// Zoom controls
	function zoomIn() {
		scale = Math.min(scale + 0.25, 3);
		renderPage(currentPage);
	}

	function zoomOut() {
		scale = Math.max(scale - 0.25, 0.5);
		renderPage(currentPage);
	}

	// Watch for PDF source changes
	$effect(() => {
		if (pdfSource) {
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
	bind:this={containerRef}
	class="pdf-highlighter-container relative flex h-full w-full flex-col items-center rounded-lg bg-gray-100 shadow-lg"
>
	{#if isLoading}
		<div class="absolute inset-0 flex items-center justify-center bg-white">
			<div class="text-center">
				<div
					class="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-b-2 border-gray-900"
				></div>
				<p class="text-gray-600">Loading PDF...</p>
			</div>
		</div>
	{/if}

	{#if error}
		<div class="absolute inset-0 flex items-center justify-center bg-white">
			<div class="p-6 text-center">
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
	{/if}

	{#if !isLoading && !error && pdfDocument}
		<!-- Toolbar -->
		<div
			class="toolbar flex items-center justify-between gap-4 border-b border-gray-200 bg-white px-4 py-3"
		>
			<!-- Page navigation -->
			<div class="flex items-center gap-2">
				<button
					onclick={previousPage}
					disabled={currentPage <= 1}
					class="rounded bg-gray-100 px-3 py-1.5 text-sm font-medium transition-colors hover:bg-gray-200 disabled:cursor-not-allowed disabled:opacity-50"
					aria-label="Previous page"
				>
					←
				</button>
				<span class="text-sm text-gray-700">
					Page {currentPage} / {totalPages}
				</span>
				<button
					onclick={nextPage}
					disabled={currentPage >= totalPages}
					class="rounded bg-gray-100 px-3 py-1.5 text-sm font-medium transition-colors hover:bg-gray-200 disabled:cursor-not-allowed disabled:opacity-50"
					aria-label="Next page"
				>
					→
				</button>
			</div>

			<!-- Zoom controls -->
			<div class="flex items-center gap-2">
				<button
					onclick={zoomOut}
					class="rounded bg-gray-100 px-3 py-1.5 text-sm font-medium transition-colors hover:bg-gray-200"
					aria-label="Zoom out"
				>
					−
				</button>
				<span class="min-w-[60px] text-center text-sm text-gray-700">
					{Math.round(scale * 100)}%
				</span>
				<button
					onclick={zoomIn}
					class="rounded bg-gray-100 px-3 py-1.5 text-sm font-medium transition-colors hover:bg-gray-200"
					aria-label="Zoom in"
				>
					+
				</button>
			</div>

			<!-- Color picker -->
			<div class="flex items-center gap-2">
				<p class="text-sm text-gray-700">Highlight:</p>
				<input
					type="color"
					bind:value={highlightColor}
					class="h-8 w-8 cursor-pointer rounded"
					aria-label="Highlight color"
				/>
			</div>

			<!-- Annotations count -->
			<div class="text-sm text-gray-700">
				{comments.length}
				{comments.length === 1 ? 'highlight' : 'highlights'}
			</div>
		</div>

		<!-- PDF viewer -->
		<div
			class="pdf-viewer flex h-full w-full justify-center bg-gray-100"
			onwheel={(e) => {
				// prevent default behaviour if ctrl key is pressed
				// adjust pdf zoom based on scroll direction
				if (e.ctrlKey) {
					e.preventDefault();
					if (e.deltaY < 0) {
						zoomIn();
					} else {
						zoomOut();
					}
				}
			}}
		>
			<div class="relative inline-block min-w-min">
				<!-- PDF Canvas -->
				<canvas bind:this={canvasRef} class="block"></canvas>

				<!-- Text Layer (for selection) -->
				<div
					bind:this={textLayerRef}
					class="text-layer pointer-events-auto absolute left-0 top-0"
					style:width="{textLayerWidth}px"
					style:height="{textLayerHeight}px"
					onmouseup={handleTextSelection}
					role="textbox"
					tabindex="0"
					aria-label="PDF text content"
				>
					{#each textLayerItems as item (item.id)}
						<div
							class="pointer-events-auto absolute origin-top-left cursor-text select-text whitespace-pre text-transparent"
							style:left="{item.left}px"
							style:top="{item.top}px"
							style:font-size="{item.fontSize}px"
							style:font-family={item.fontFamily}
							style:transform="rotate({item.angle}rad)"
						>
							{item.text}
						</div>
					{/each}
				</div>

				<!-- Annotations Layer -->
				<div class="annotations-layer pointer-events-none absolute left-0 top-0 h-full w-full">
					{#each comments.filter(({ annotation }) => annotation?.pageNumber === currentPage) as comment (comment.id)}
						{@const annotation = comment.annotation as unknown as Annotation}
						{@const scaledBoxes = annotation.boundingBoxes.map((box) => ({
							x: box.x * textLayerWidth,
							y: box.y * textLayerHeight,
							width: box.width * textLayerWidth,
							height: box.height * textLayerHeight
						}))}
						{@const lowerLeftBox = scaledBoxes.reduce((prev, curr) => {
							const prevBottom = prev.y + prev.height;
							const currBottom = curr.y + curr.height;
							if (currBottom > prevBottom || (currBottom === prevBottom && curr.x < prev.x)) {
								return curr;
							}
							return prev;
						})}
						<button
							class="annotation-group group pointer-events-auto"
							title={annotation.text}
							onclick={() => onAnnotationSelect(comment)}
							onkeydown={(e) => e.key === 'Enter' && onAnnotationSelect(comment)}
							aria-label={`Annotation: ${annotation.text}`}
						>
							{#each scaledBoxes as box, boxIdx (`${comment.id}-${boxIdx}`)}
								{@const margin = 3}
								<div
									class="absolute cursor-pointer rounded-sm border-black transition-opacity group-hover:border-2"
									style:left="{box.x - margin}px"
									style:top="{box.y - margin}px"
									style:width="{box.width + margin * 2}px"
									style:height="{box.height + margin * 2}px"
									style:background-color={annotation.color}
									style:opacity="0.25"
								></div>
							{/each}

							<!-- <div
								class="absolute"
								style:left="-20px"
								style:top="{lowerLeftBox.y + lowerLeftBox.height}px"
							>
								<div
									class="absolute w-0.5 bg-gray-400"
									style:height="{20}px"
									style:top="0"
									style:left="20px"
								></div>
								<div
									class="rounded border border-gray-300 bg-white p-2 text-sm text-gray-700 shadow-md"
									style:position="relative"
								>
									{comment.content ?? 'No comment'}
								</div>
							</div> -->
						</button>
					{/each}
				</div>
			</div>
		</div>
	{/if}
</div>

<style>
	.text-layer {
		line-height: 1;
	}

	.text-layer :global(::selection) {
		background: rgba(0, 123, 255, 0.3);
	}

	/* Scrollbar styling */
	.pdf-viewer::-webkit-scrollbar {
		width: 12px;
		height: 12px;
	}

	.pdf-viewer::-webkit-scrollbar-track {
		background: #f1f1f1;
	}

	.pdf-viewer::-webkit-scrollbar-thumb {
		background: #888;
		border-radius: 6px;
	}

	.pdf-viewer::-webkit-scrollbar-thumb:hover {
		background: #555;
	}
</style>
