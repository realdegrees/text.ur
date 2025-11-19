<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { browser } from '$app/environment';
	import type { CommentRead } from '$api/types';
	import type { Annotation } from '$types/pdf';
	import { mergeHighlightBoxes } from '$lib/util/pdfUtils';
	import TextLayer from './TextLayer.svelte';
	import HighlightLayer from './HighlightLayer.svelte';
	import SingleComment from '../comments/SingleComment.svelte';

	// Props
	interface Props {
		pdfSource: Blob;
		onAnnotationCreate?: (annotation: Annotation) => void;
		onCommentDelete?: (commentId: number) => Promise<void>;
		comments: CommentRead[];
		currentPage?: number;
		scale?: number;
		highlightColor?: string;
		hoveredCommentId?: number | null;
		focusedCommentId?: number | null;
		totalPages?: number;
		pageDataArray?: Array<{ pageNumber: number; width: number; height: number }>;
		pdfContainerRef?: HTMLDivElement | null;
		documentScrollRef?: HTMLDivElement | null;
		commentsSectionRef?: HTMLDivElement | null;
		onZoomChange?: (scale: number) => void;
	}

	let {
		pdfSource,
		onAnnotationCreate = () => {},
		onCommentDelete,
		comments = [],
		currentPage = $bindable(1),
		scale = $bindable(1.5),
		highlightColor = $bindable('#FFFF00'),
		hoveredCommentId = $bindable(null),
		focusedCommentId = $bindable(null),
		totalPages = $bindable(0),
		pageDataArray = $bindable([]),
		pdfContainerRef = $bindable(null),
		documentScrollRef = $bindable(null),
		commentsSectionRef = $bindable(null),
		onZoomChange = () => {}
	}: Props = $props();

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

	// Page data structure
	interface PageData {
		pageNumber: number;
		canvas: HTMLCanvasElement | null;
		textLayerRef: HTMLDivElement | null;
		textLayerItems: TextLayerItem[];
		width: number;
		height: number;
	}

	// State
	let containerRef: HTMLDivElement | null = $state(null);
	let pdfDocument: any = $state(null);
	let isLoading: boolean = $state(true);
	let error: string = $state('');
	let pages: PageData[] = $state([]);

	// Selection state
	let selectionInfo: SelectionInfo | null = $state(null);

	// Comment interaction state
	let deleteConfirmId = $state<number | null>(null);

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

	// Track if initial render is complete
	let initialRenderComplete = $state(false);

	// Load PDF from Blob
	async function loadPDF() {
		if (!pdfjsLib) return;

		try {
			isLoading = true;
			initialRenderComplete = false;
			const arrayBuffer = await pdfSource.arrayBuffer();
			const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
			pdfDocument = await loadingTask.promise;
			totalPages = pdfDocument.numPages;

			// Initialize page data array
			pages = Array.from({ length: totalPages }, (_, i) => ({
				pageNumber: i + 1,
				canvas: null,
				textLayerRef: null,
				textLayerItems: [],
				width: 0,
				height: 0
			}));

			// Wait for Svelte to render the DOM with the canvases
			// Use a longer timeout to ensure canvas bindings are ready
			await new Promise((resolve) => setTimeout(resolve, 100));

			// Render all pages
			await renderAllPages();
			initialRenderComplete = true;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load PDF';
			console.error('PDF loading error:', err);
		} finally {
			isLoading = false;
		}
	}

	// Render all pages sequentially to avoid canvas conflicts
	async function renderAllPages() {
		if (!pdfDocument) return;

		// Render pages sequentially to avoid "Cannot use the same canvas" error
		for (let i = 0; i < totalPages; i++) {
			// Wait for canvas to be available
			let attempts = 0;
			while (!pages[i]?.canvas && attempts < 20) {
				await new Promise((resolve) => setTimeout(resolve, 50));
				attempts++;
			}

			if (!pages[i]?.canvas) {
				console.warn(`Canvas for page ${i + 1} not available after waiting`);
				continue;
			}

			await renderPage(i);
		}
	}

	// Render a specific page by index
	async function renderPage(pageIndex: number) {
		if (!pdfDocument || !pdfjsLib) return;

		try {
			const pageData = pages[pageIndex];
			if (!pageData || !pageData.canvas) return;

			const page = await pdfDocument.getPage(pageData.pageNumber);
			const viewport = page.getViewport({ scale });

			const canvas = pageData.canvas;
			const context = canvas.getContext('2d');
			if (!context) return;

			// Set canvas dimensions to match viewport
			canvas.height = viewport.height;
			canvas.width = viewport.width;

			// Update page dimensions
			pageData.width = viewport.width;
			pageData.height = viewport.height;

			// Clear canvas before rendering
			context.clearRect(0, 0, canvas.width, canvas.height);

			// Render PDF page
			const renderContext = {
				canvasContext: context,
				viewport: viewport
			};

			const renderTask = page.render(renderContext);
			await renderTask.promise;

			// Render text layer for selection
			await renderTextLayer(pageIndex, page, viewport);
		} catch (err: any) {
			// Ignore cancelled render errors when zooming
			if (err?.name !== 'RenderingCancelledException') {
				console.error('Page rendering error:', err);
			}
		}
	}

	// Render text layer for text selection
	async function renderTextLayer(pageIndex: number, page: any, viewport: any) {
		const pageData = pages[pageIndex];
		if (!pageData) return;

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

	// Handle mouse move to detect which highlight is being hovered
	function handleMouseMove(event: MouseEvent, pageIndex: number) {
		const pageData = pages[pageIndex];
		if (!pageData?.textLayerRef) return;

		const rect = pageData.textLayerRef.getBoundingClientRect();
		const localMouseX = event.clientX - rect.left;
		const localMouseY = event.clientY - rect.top;

		// Check which highlight (if any) the mouse is over
		const currentPageComments = comments.filter(
			({ annotation }) => (annotation as unknown as Annotation)?.pageNumber === pageData.pageNumber
		);

		let foundHover = false;
		for (const comment of currentPageComments) {
			const annotation = comment.annotation as unknown as Annotation;
			const scaledBoxes = annotation.boundingBoxes.map((box) => ({
				x: box.x * pageData.width,
				y: box.y * pageData.height,
				width: box.width * pageData.width,
				height: box.height * pageData.height
			}));

			// Check if mouse is over any box with margin
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

	// Handle text selection
	function handleTextSelection(pageIndex: number) {
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

		const pageData = pages[pageIndex];
		if (!pageData) return;

		selectionInfo = {
			text: selectedText,
			boundingBox: boundingBox,
			pageNumber: pageData.pageNumber
		};

		createHighlight(pageIndex);
	}

	// Create highlight annotation
	function createHighlight(pageIndex: number) {
		if (!selectionInfo) return;

		const selection = window.getSelection();
		if (!selection || !selection.rangeCount) return;

		const pageData = pages[pageIndex];
		if (!pageData?.textLayerRef || pageData.width === 0 || pageData.height === 0) return;

		const textLayerRect = pageData.textLayerRef.getBoundingClientRect();
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
			x: box.x / pageData.width,
			y: box.y / pageData.height,
			width: box.width / pageData.width,
			height: box.height / pageData.height
		}));

		const annotation: Annotation = {
			pageNumber: pageData.pageNumber,
			text: selectionInfo.text,
			boundingBoxes: normalizedBoxes,
			color: highlightColor,
			timestamp: Date.now()
		};

		// Update current page to match the page where highlight was created
		if (currentPage !== pageData.pageNumber) {
			currentPage = pageData.pageNumber;
		}

		onAnnotationCreate(annotation);

		// Clear selection
		window.getSelection()?.removeAllRanges();
		selectionInfo = null;
	}


	// Scroll to a specific page
	export function scrollToPage(pageNum: number) {
		if (pageNum < 1 || pageNum > totalPages || !pdfContainerRef) return;

		const pageElement = pdfContainerRef.querySelector(`[data-page-number="${pageNum}"]`);
		if (pageElement) {
			pageElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
		}
	}

	// Comment positioning logic
	interface PositionedComment {
		comment: CommentRead;
		idealTop: number;
		actualTop: number;
		highlightBottom: number;
		highlightRightX: number;
	}

	function getPageDimensions(pageNumber: number) {
		const pageData = pageDataArray.find((p) => p.pageNumber === pageNumber);
		return pageData || { width: 0, height: 0 };
	}

	function getPageOffsetTop(pageNumber: number): number {
		if (!documentScrollRef || !pdfContainerRef) return 0;

		const pageElement = pdfContainerRef.querySelector(`[data-page-number="${pageNumber}"]`);
		if (!pageElement) return 0;

		const scrollRect = documentScrollRef.getBoundingClientRect();
		const pageRect = pageElement.getBoundingClientRect();

		return pageRect.top - scrollRect.top + documentScrollRef.scrollTop;
	}

	function isCommentExpanded(commentId: number): boolean {
		return focusedCommentId === commentId || hoveredCommentId === commentId;
	}

	function getIdealCommentTopPosition(comment: CommentRead, commentHeight: number): number {
		const annotation = comment.annotation as unknown as Annotation;
		if (!annotation || !annotation.boundingBoxes || annotation.boundingBoxes.length === 0) {
			return 0;
		}

		const pageData = getPageDimensions(annotation.pageNumber);
		if (pageData.height === 0) return 0;

		const bottomBox = annotation.boundingBoxes.reduce((prev, curr) => {
			const prevBottom = prev.y + prev.height;
			const currBottom = curr.y + curr.height;
			return currBottom > prevBottom ? curr : prev;
		});

		const bottomPositionInPage = (bottomBox.y + bottomBox.height) * pageData.height;
		const pageOffsetTop = getPageOffsetTop(annotation.pageNumber);
		const highlightBottom = pageOffsetTop + bottomPositionInPage;
		return highlightBottom - commentHeight;
	}

	function getHighlightBottomPosition(
		comment: CommentRead,
		commentsSectionRef: HTMLElement | null
	): { rightX: number; bottom: number } {
		const annotation = comment.annotation as unknown as Annotation;
		if (!annotation || !annotation.boundingBoxes || annotation.boundingBoxes.length === 0) {
			return { rightX: 0, bottom: 0 };
		}

		const pageData = getPageDimensions(annotation.pageNumber);
		if (pageData.width === 0 || pageData.height === 0) return { rightX: 0, bottom: 0 };

		if (!documentScrollRef || !pdfContainerRef || !commentsSectionRef)
			return { rightX: 0, bottom: 0 };

		const bottomBox = annotation.boundingBoxes.reduce((prev, curr) => {
			const prevBottom = prev.y + prev.height;
			const currBottom = curr.y + curr.height;
			return currBottom > prevBottom ? curr : prev;
		});

		const rightBox = annotation.boundingBoxes.reduce((prev, curr) => {
			const prevRight = prev.x + prev.width;
			const currRight = curr.x + curr.width;
			return currRight > prevRight ? curr : prev;
		});

		const pageElement = pdfContainerRef.querySelector(
			`[data-page-number="${annotation.pageNumber}"]`
		);
		if (!pageElement) return { rightX: 0, bottom: 0 };

		const pageOffsetTop = getPageOffsetTop(annotation.pageNumber);
		const commentsRect = commentsSectionRef.getBoundingClientRect();
		const pageRect = pageElement.getBoundingClientRect();

		const highlightRightWithinPage = (rightBox.x + rightBox.width) * pageData.width;
		const highlightRightX = pageRect.left - commentsRect.left + highlightRightWithinPage;

		return {
			rightX: highlightRightX,
			bottom: pageOffsetTop + (bottomBox.y + bottomBox.height) * pageData.height
		};
	}

	let positionedComments = $derived.by((): PositionedComment[] => {
		if (!documentScrollRef || !pdfContainerRef || !commentsSectionRef || pageDataArray.length === 0)
			return [];

		const COMMENT_HEIGHT = 60;
		const MIN_GAP = 8;

		const sorted = comments
			.map((comment) => {
				const highlightPos = getHighlightBottomPosition(comment, commentsSectionRef);
				return {
					comment,
					idealTop: getIdealCommentTopPosition(comment, COMMENT_HEIGHT),
					actualTop: 0,
					highlightBottom: highlightPos.bottom,
					highlightRightX: highlightPos.rightX
				};
			})
			.sort((a, b) => a.idealTop - b.idealTop);

		for (let i = 0; i < sorted.length; i++) {
			if (i === 0) {
				sorted[i].actualTop = sorted[i].idealTop;
			} else {
				const prevBottom = sorted[i - 1].actualTop + COMMENT_HEIGHT + MIN_GAP;
				sorted[i].actualTop = Math.max(sorted[i].idealTop, prevBottom);
			}
		}

		return sorted;
	});

	// Comment interaction handlers
	function handleCommentClick(commentId: number, event: MouseEvent) {
		event.stopPropagation();
		focusedCommentId = focusedCommentId === commentId ? null : commentId;
	}

	function handleMouseEnter(commentId: number) {
		hoveredCommentId = commentId;
	}

	function handleMouseLeave() {
		hoveredCommentId = null;
	}

	function handleDeleteClick(commentId: number, event: MouseEvent) {
		event.stopPropagation();
		deleteConfirmId = commentId;
	}

	async function handleDeleteConfirm(commentId: number, event: MouseEvent) {
		event.stopPropagation();
		if (onCommentDelete) {
			await onCommentDelete(commentId);
		}
		focusedCommentId = null;
		hoveredCommentId = null;
		deleteConfirmId = null;
	}

	function handleDeleteCancel(event: MouseEvent) {
		event.stopPropagation();
		deleteConfirmId = null;
	}

	function handleDocumentClick(event: MouseEvent) {
		const target = event.target as HTMLElement;
		const isCommentClick = target.closest('[data-comment-id]');
		const isHighlightClick = target.closest('.annotation-group');

		if (!isCommentClick && !isHighlightClick) {
			focusedCommentId = null;
			deleteConfirmId = null;
		}
	}

	// Update page data array for comments positioning
	$effect(() => {
		if (pages.length > 0) {
			pageDataArray = pages.map((p) => ({
				pageNumber: p.pageNumber,
				width: p.width,
				height: p.height
			}));
		}
	});

	// Re-render all pages when scale changes (but not on initial load)
	$effect(() => {
		if (pdfDocument && pages.length > 0 && scale && initialRenderComplete) {
			renderAllPages();
			onZoomChange(scale);
		}
	});

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
		if (browser) {
			document.removeEventListener('click', handleDocumentClick);
		}
	});

	// Setup global click listener
	$effect(() => {
		if (browser) {
			document.addEventListener('click', handleDocumentClick);
			return () => {
				document.removeEventListener('click', handleDocumentClick);
			};
		}
	});
</script>

<div class="flex h-full w-full flex-row items-start gap-0">
	<!-- Comments Section -->
	<div class="relative flex-1 bg-gray-50 pr-4 overflow-visible" bind:this={commentsSectionRef}>
		{#each positionedComments as { comment, actualTop, highlightBottom, highlightRightX } (comment.id)}
			{@const annotation = comment.annotation as unknown as Annotation}
			{@const expanded = isCommentExpanded(comment.id)}
			{@const showDeleteConfirm = deleteConfirmId === comment.id}
			{@const COMMENT_HEIGHT = 60}
			{@const commentBottom = actualTop + COMMENT_HEIGHT}
			{@const horizontalLineY = highlightBottom}
			{@const commentsSectionWidth = commentsSectionRef?.getBoundingClientRect().width || 0}
			{@const commentLeftEdge = commentsSectionWidth - 12}

			<!-- Connection line from highlight to comment (only when expanded) -->
			{#if expanded && highlightRightX > 0}
				<svg
					class="pointer-events-none absolute left-0 top-0 z-50 overflow-visible"
					style:width="200vw"
					style:height="{Math.max(commentBottom, horizontalLineY) + 20}px"
				>
					<!-- Direct line from highlight to comment -->
					<line
						x1={highlightRightX}
						y1={highlightBottom}
						x2={commentLeftEdge}
						y2={commentBottom}
						stroke={annotation.color}
						stroke-width="3"
						stroke-opacity="0.8"
					/>
				</svg>
			{/if}

			<SingleComment
				{comment}
				{annotation}
				{expanded}
				{showDeleteConfirm}
				{actualTop}
				onCommentClick={(e) => handleCommentClick(comment.id, e)}
				onMouseEnter={() => handleMouseEnter(comment.id)}
				onMouseLeave={handleMouseLeave}
				onDeleteClick={(e) => handleDeleteClick(comment.id, e)}
				onDeleteConfirm={(e) => handleDeleteConfirm(comment.id, e)}
				onDeleteCancel={handleDeleteCancel}
			/>
		{/each}
	</div>

	<!-- PDF Viewer Section -->
	<div
		bind:this={containerRef}
		class="pdf-highlighter-container relative flex h-full w-fit flex-col rounded-lg bg-gray-100 shadow-lg"
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
		<!-- PDF Controls Header -->
		<div class="flex items-center justify-between border-b border-gray-200 bg-white px-4 py-3">
			<!-- Page navigation -->
			<div class="flex items-center gap-2">
				<button
					onclick={() => scrollToPage(currentPage - 1)}
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
					onclick={() => scrollToPage(currentPage + 1)}
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
					onclick={() => {
						scale = Math.max(scale - 0.25, 0.5);
					}}
					class="rounded bg-gray-100 px-3 py-1.5 text-sm font-medium transition-colors hover:bg-gray-200"
					aria-label="Zoom out"
				>
					−
				</button>
				<span class="min-w-[60px] text-center text-sm text-gray-700">
					{Math.round(scale * 100)}%
				</span>
				<button
					onclick={() => {
						scale = Math.min(scale + 0.25, 3);
					}}
					class="rounded bg-gray-100 px-3 py-1.5 text-sm font-medium transition-colors hover:bg-gray-200"
					aria-label="Zoom in"
				>
					+
				</button>
			</div>
		</div>

		<!-- PDF pages -->
		<div
			bind:this={pdfContainerRef}
			class="pdf-pages flex w-full flex-col items-center gap-4 bg-gray-100 p-4"
		>
			{#each pages as pageData, pageIndex (pageData.pageNumber)}
				<div
					class="page-container relative bg-white shadow-lg"
					data-page-number={pageData.pageNumber}
				>
					<!-- PDF Canvas -->
					<canvas bind:this={pageData.canvas} class="block"></canvas>

					<!-- Text Layer (for selection) -->
					<TextLayer
						bind:textLayerRef={pageData.textLayerRef}
						textLayerItems={pageData.textLayerItems}
						textLayerWidth={pageData.width}
						textLayerHeight={pageData.height}
						onTextSelection={() => handleTextSelection(pageIndex)}
						onMouseMove={(e) => handleMouseMove(e, pageIndex)}
						onMouseLeave={() => (hoveredCommentId = null)}
					/>

					<!-- Annotations Layer -->
					<HighlightLayer
						{comments}
						currentPage={pageData.pageNumber}
						textLayerWidth={pageData.width}
						textLayerHeight={pageData.height}
						{hoveredCommentId}
						{focusedCommentId}
					/>
				</div>
			{/each}
		</div>
	{/if}
	</div>
</div>
