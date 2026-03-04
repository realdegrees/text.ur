<script lang="ts">
	import type { PDFSlick } from '@pdfslick/core';
	import { onDestroy, onMount } from 'svelte';
	import '@pdfslick/core/dist/pdf_viewer.css';
	import AnnotationLayer from './AnnotationLayer.svelte';
	import TextSelectionHandler from './TextSelectionHandler.svelte';
	import CommentSidebar from './CommentSidebar.svelte';
	import TasksPanel from './TasksPanel.svelte';
	import ConnectionLines from './ConnectionLines.svelte';
	import MobileCommentPanel from './MobileCommentPanel.svelte';
	import PdfControls from './PdfControls.svelte';
	import UserCursors from './UserCursors.svelte';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import { PDF_ZOOM_STEP, PDF_MIN_SCALE } from './constants';
	import { documentStore } from '$lib/runes/document.svelte';
	import { createScreenState } from '$lib/util/responsive.svelte';
	import LL from '$i18n/i18n-svelte';
	import IconComment from '~icons/material-symbols/comment-outline';
	import IconTask from '~icons/material-symbols/task-outline';
	import IconInfo from '~icons/material-symbols/info-outline';

	interface Props {
		document: ArrayBuffer;
	}

	let { document: pdfData }: Props = $props();

	let container: HTMLDivElement | null = $state(null);
	let pdfAreaWrapper: HTMLDivElement | null = $state(null);
	let rootContainer: HTMLDivElement | null = $state(null);
	let sidebarContainer: HTMLDivElement | null = $state(null);
	let contentAreaRef: HTMLDivElement | null = $state(null);
	let pdfSlick: PDFSlick | null = $state(null);
	let unsubscribe: (() => void) | null = $state(null);
	let mobileCommentPanel: any = $state(null);

	// Screen size detection
	const screen = createScreenState();

	// Tablets get the full-width "compact" layout (page-width scale, bottom
	// comment panel) instead of the desktop sidebar layout, which would steal
	// ~40% of a narrow tablet screen for the sidebar.
	let compactLayout = $derived(screen.isMobile || screen.isTablet);

	let pageNumber = $state(1);
	let scrollTop = $state(0);
	let pdfWidth = $state(0);
	let basePageWidth = $state(0);
	let maxAvailableWidth = $state(0);

	const updatePdfWidth = () => {
		if (!container) return;
		const page = container.querySelector('.page') as HTMLElement | null;
		if (page) {
			const pageRect = page.getBoundingClientRect();
			pdfWidth = pageRect.width + 10;

			if (documentStore.documentScale > 0) {
				basePageWidth = page.clientWidth / documentStore.documentScale;
			}
		}
	};

	const captureMaxAvailableWidth = () => {
		// Desktop: use contentAreaRef (excludes controls column); mobile: use pdfAreaWrapper's parent.
		const target = contentAreaRef ?? pdfAreaWrapper?.parentElement;
		if (!target) return;
		const available = compactLayout ? target.clientWidth : target.clientWidth - 288;
		if (available > maxAvailableWidth) {
			maxAvailableWidth = available;
		}
	};

	let maxScale = $derived(
		basePageWidth > 0 && maxAvailableWidth > 0 ? (maxAvailableWidth - 16) / basePageWidth : 10
	);

	let hasDescription = $derived(!!documentStore.loadedDocument?.description?.trim());

	const initialize = async () => {
		if (!container) return;

		const { create, PDFSlick } = await import('@pdfslick/core');
		const store = create();

		pdfSlick = new PDFSlick({
			container,
			store,
			options: {
				scaleValue: compactLayout ? 'page-width' : 'page-height',
				annotationMode: 0, // DISABLE — no links, forms, popups, or baked-in annotations
				annotationEditorMode: -1 // DISABLE — remove built-in annotation editor entirely
			}
		});

		pdfSlick.loadDocument(pdfData);
		store.setState({ pdfSlick });

		unsubscribe = store.subscribe((s) => {
			pageNumber = s.pageNumber;
			documentStore.numPages = s.numPages;

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

			documentStore.documentScale = clampedScale;
			updatePdfWidth();
			captureMaxAvailableWidth();
		});
	};

	const handleScroll = (e: Event) => {
		const target = e.target as HTMLElement;
		scrollTop = target.scrollTop;
	};

	// Forward wheel events from comments sidebar to PDF container
	const handleCommentsWheel = (e: WheelEvent) => {
		if (!container) return;

		// Check if the event target is a scrollable element (like textarea)
		const target = e.target as HTMLElement;
		const isScrollable =
			target.tagName === 'TEXTAREA' ||
			(target.scrollHeight > target.clientHeight && target.classList.contains('overflow-y-auto'));

		// If scrolling inside a scrollable element, allow natural scrolling
		if (isScrollable) {
			const atTop = target.scrollTop === 0;
			const atBottom = target.scrollTop + target.clientHeight >= target.scrollHeight;

			// Only prevent default if trying to scroll beyond the bounds
			if ((e.deltaY < 0 && !atTop) || (e.deltaY > 0 && !atBottom)) {
				return; // Let the element handle its own scrolling
			}
		}

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
		pdfSlick.currentScale = documentStore.documentScale + PDF_ZOOM_STEP;
	};

	const zoomOut = () => {
		if (!pdfSlick) return;
		pdfSlick.currentScale = documentStore.documentScale - PDF_ZOOM_STEP;
	};

	const fitHeight = () => {
		if (pdfSlick) pdfSlick.currentScaleValue = 'page-height';
	};

	const prevPage = () => pdfSlick?.gotoPage(Math.max(pageNumber - 1, 1));
	const nextPage = () => pdfSlick?.gotoPage(Math.min(pageNumber + 1, documentStore.numPages));

	$effect(() => {
		// Desktop: observe the two-column content area (controls already excluded).
		// Mobile: fall back to pdfAreaWrapper's parent.
		const target = contentAreaRef ?? pdfAreaWrapper?.parentElement;
		if (!target) return;
		const resizeObserver = new ResizeObserver(() => {
			if (compactLayout) {
				maxAvailableWidth = target.clientWidth;
			} else {
				// contentAreaRef width already excludes the controls column (48px).
				// Subtract min sidebar width (min-w-72 = 288px).
				maxAvailableWidth = target.clientWidth - 288;
			}
		});
		resizeObserver.observe(target);
		return () => resizeObserver.disconnect();
	});

	// Store refs in document store
	$effect(() => {
		documentStore.scrollContainerRef = container;
		documentStore.mobileCommentPanelRef = mobileCommentPanel;
	});

	// Auto-switch to comments tab when the active tab's content disappears
	$effect(() => {
		if (documentStore.activeTab === 'tasks' && documentStore.tasks.length === 0) {
			documentStore.activeTab = 'comments';
		}
		if (documentStore.activeTab === 'info' && !hasDescription) {
			documentStore.activeTab = 'comments';
		}
	});

	onMount(initialize);
	onDestroy(() => unsubscribe?.());
</script>

<div
	class="pdf-viewer-container flex h-full w-full bg-background {compactLayout
		? 'relative'
		: 'flex-col'}"
	bind:this={rootContainer}
>
	<!-- Responsive controls: Compact overlay or desktop column -->
	{#if compactLayout}
		<!-- Mobile: small spacer for overlay controls to not overlap content -->
		<div class="w-12 shrink-0"></div>
		<PdfControls
			minScale={PDF_MIN_SCALE}
			{maxScale}
			{pageNumber}
			numPages={documentStore.numPages}
			onZoomIn={zoomIn}
			onZoomOut={zoomOut}
			onFitHeight={fitHeight}
			onPrevPage={prevPage}
			onNextPage={nextPage}
			isMobile={true}
		/>
	{:else}
		<div class="flex flex-1 overflow-hidden">
			<!-- Controls column - should take full container height -->
			<PdfControls
				minScale={PDF_MIN_SCALE}
				{maxScale}
				{pageNumber}
				numPages={documentStore.numPages}
				onZoomIn={zoomIn}
				onZoomOut={zoomOut}
				onFitHeight={fitHeight}
				onPrevPage={prevPage}
				onNextPage={nextPage}
				isMobile={false}
			/>
			<!-- Two-column content area: PDF (left) | Sidebar (right) -->
			<div class="flex flex-1 overflow-hidden" bind:this={contentAreaRef}>
				<!-- LEFT column: PDF viewer takes full height -->
				<div
					class="relative overflow-hidden bg-text/5 transition-[width] duration-150"
					style="width: {pdfWidth > 0 ? `${pdfWidth}px` : '100%'}; max-width: 100%;"
					bind:this={pdfAreaWrapper}
				>
					<div
						id="viewerContainer"
						class="pdfSlickContainer absolute inset-0 custom-scrollbar overflow-x-hidden overflow-y-scroll"
						bind:this={container}
						onscroll={handleScroll}
						onwheel={handlePdfWheel}
					>
						<div id="viewer" class="pdfSlickViewer pdfViewer m-0! p-0!"></div>
					</div>
					<!-- Annotation highlights are rendered into the PDF pages -->
					<AnnotationLayer viewerContainer={container} />

					<!-- Text selection handler for creating new annotations -->
					<TextSelectionHandler viewerContainer={container} />

					<!-- Other users' cursors -->
					<UserCursors viewerContainer={container} />
				</div>

				<!-- RIGHT column: tab bar + content panel -->
				<div
					class="relative flex min-w-72 flex-1 flex-col overflow-hidden bg-background"
					bind:this={sidebarContainer}
				>
					<!-- Tab bar: Info | Tasks | Comments -->
					<div class="flex border-b border-text/10 bg-inset">
						{#if hasDescription}
							<button
								class="flex flex-1 items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium transition-colors {documentStore.activeTab ===
								'info'
									? 'border-b-2 border-primary text-primary'
									: 'text-text/50 hover:text-text/70'}"
								onclick={() => (documentStore.activeTab = 'info')}
							>
								<IconInfo class="h-3.5 w-3.5" />
								{$LL.pdf.documentInfo()}
							</button>
						{/if}
						{#if documentStore.tasks.length > 0}
							<button
								class="flex flex-1 items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium transition-colors {documentStore.activeTab ===
								'tasks'
									? 'border-b-2 border-primary text-primary'
									: 'text-text/50 hover:text-text/70'}"
								onclick={() => (documentStore.activeTab = 'tasks')}
							>
								<IconTask class="h-3.5 w-3.5" />
								{$LL.tasks.title()}
							</button>
						{/if}
						<button
							class="flex flex-1 items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium transition-colors {documentStore.activeTab ===
							'comments'
								? 'border-b-2 border-primary text-primary'
								: 'text-text/50 hover:text-text/70'}"
							onclick={() => (documentStore.activeTab = 'comments')}
						>
							<IconComment class="h-3.5 w-3.5" />
							{$LL.tasks.comments()}
						</button>
					</div>
					<!-- Content panel (pl-4 offsets content from PDF edge; tab bar stays flush) -->
					{#if documentStore.activeTab === 'info'}
						<div class="flex-1 overflow-y-auto py-2 pr-3 pl-4">
							<MarkdownRenderer
								content={documentStore.loadedDocument?.description ?? ''}
								class="text-sm text-text/80"
							/>
						</div>
					{:else if documentStore.activeTab === 'comments'}
						<div
							class="relative flex-1 overflow-hidden pl-4"
							onwheel={handleCommentsWheel}
							role="complementary"
						>
							<CommentSidebar viewerContainer={container} {scrollTop} />
						</div>
					{:else}
						<div class="flex-1 overflow-hidden pl-4">
							<TasksPanel />
						</div>
					{/if}
				</div>
			</div>
		</div>

		<!-- Shared connection lines overlay (desktop) -->
		<ConnectionLines {scrollTop} />
	{/if}

	<!-- Compact PDF viewer and bottom comment panel (mobile + tablet) -->
	{#if compactLayout}
		<div class="flex w-full flex-1 flex-col overflow-y-auto">
			<div
				class="relative flex-1 overflow-hidden bg-text/5 transition-[width] duration-150"
				style="width: 100%; max-width: 100%;"
				bind:this={pdfAreaWrapper}
			>
				<div
					id="viewerContainer"
					class="pdfSlickContainer absolute inset-0 custom-scrollbar overflow-x-hidden overflow-y-scroll {compactLayout
						? 'pb-24'
						: ''}"
					bind:this={container}
					onscroll={handleScroll}
					onwheel={handlePdfWheel}
				>
					<div id="viewer" class="pdfSlickViewer pdfViewer m-0! p-0!"></div>
				</div>
				<AnnotationLayer viewerContainer={container} />
				<TextSelectionHandler viewerContainer={container} />
				<UserCursors viewerContainer={container} />
			</div>
		</div>

		<MobileCommentPanel
			bind:this={mobileCommentPanel}
			activeContentTab={documentStore.activeTab}
			onTabChange={(tab) => (documentStore.activeTab = tab)}
		/>

		<!-- Shared connection lines overlay (mobile) -->
		<ConnectionLines {scrollTop} />
	{/if}
</div>

<style>
	/* Override PDF.js CSS variables to reduce spacing */
	:global(.pdf-viewer-container) {
		--page-margin: 0px 0 6px 0;
		--page-padding: 0px 0;
		--page-border: none;
		--pdfViewer-padding-bottom: 0;
	}

	:global(.pdf-viewer-container .pdfViewer .page) {
		margin: var(--page-margin);
		border: var(--page-border);
	}

	/* Let the browser use its default bilinear/bicubic interpolation for
	   canvas scaling. Nearest-neighbor modes (crisp-edges, pixelated) cause
	   text to appear jagged when the high-DPI backing store is CSS-scaled. */

	/* Touch-friendly defaults for the PDF text layer:
	   - Remove the tap-highlight flash on mobile browsers
	   - Prevent iOS callout menu on long-press of links/images in the text layer */
	:global(.pdf-viewer-container .textLayer) {
		-webkit-tap-highlight-color: transparent;
		-webkit-touch-callout: none;
	}

	/* Defence-in-depth: hide the PDF.js annotation layer so that native PDF
	   links, form fields, popups, and pre-existing annotations can never
	   interfere with the application, even if a library update changes defaults. */
	:global(.pdf-viewer-container .annotationLayer) {
		display: none !important;
	}
</style>
