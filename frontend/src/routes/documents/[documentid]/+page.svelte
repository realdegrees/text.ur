<script lang="ts">
	import { api } from '$api/client';
	import { notification } from '$lib/stores/notificationStore';
	import { commentStore } from '$lib/stores/commentStore';
	import { documentWebSocket } from '$lib/stores/documentWebSocket';
	import PdfViewer from '$lib/components/pdf/PdfViewer.svelte';
	import CommentSidebar from '$lib/components/pdf/CommentSidebar.svelte';
	import ControlsPanel from '$lib/components/pdf/ControlsPanel.svelte';
	import ResizableDivider from '$lib/components/pdf/ResizableDivider.svelte';
	import { onMount, onDestroy } from 'svelte';

	let { data } = $props();
	let commentsWithAnnotation = $state($commentStore);

	// Layout state
	let containerRef: HTMLDivElement | null = $state(null);
	let containerWidth = $state(0);

	// Load sidebar width from localStorage or calculate center
	let commentSidebarWidth = $state(400); // Temporary default, will be overridden
	let sidebarWidthInitialized = $state(false);

	// PDF viewer state
	let documentScrollRef: HTMLDivElement | null = $state(null);
	let pdfContainerRef: HTMLDivElement | null = $state(null);
	let sidebarRef: HTMLDivElement | null = $state(null);
	let currentPage = $state(1);
	let totalPages = $state(0);
	let scale = $state(1.5);
	let cssScaleFactor = $state(1);
	let documentScrollTop = $state(0);
	let highlightColor = $state('#FFFF00');

	// Page data array is provided by commentStore; keep a local reactive copy
	let pageDataArray = $state<Array<{ pageNumber: number; width: number; height: number }>>([]);
	let pageDataCacheVersion = $state(0);

	commentStore.subscribeToCacheVersion((v) => {
		pageDataCacheVersion = v;
	});

	$effect(() => {
		// Update local copy when the store's page data changes
		void pageDataCacheVersion;
		pageDataArray = commentStore.getPageDataArray() ?? [];
	});

	// Handle divider drag
	let dragStartWidth = $state(0);
	let isDragging = $state(false);

	function handleDragStart() {
		dragStartWidth = commentSidebarWidth;
	}

	function handleDragMove(deltaX: number) {
		const newWidth = dragStartWidth - deltaX;
		// Calculate minimum widths as 20% of available space (excluding controls)
		const availableSpace = containerWidth - CONTROLS_WIDTH;
		const minCommentWidth = availableSpace * 0.2;
		const minPdfWidth = availableSpace * 0.2;
		const maxCommentWidth = containerWidth - CONTROLS_WIDTH - minPdfWidth;
		commentSidebarWidth = Math.max(minCommentWidth, Math.min(maxCommentWidth, newWidth));
	}

	// Track container width for responsive positioning
	$effect(() => {
		if (!containerRef) return;

		const observer = new ResizeObserver((entries) => {
			for (const entry of entries) {
				containerWidth = entry.contentRect.width;
			}
		});

		observer.observe(containerRef);

		return () => observer.disconnect();
	});

	// Register the scroll container in the comment store
	$effect(() => {
		if (documentScrollRef) commentStore.registerScrollContainerRef(documentScrollRef);
		return () => {
			commentStore.registerScrollContainerRef(null);
		};
	});

	// Register PDF container ref
	$effect(() => {
		if (pdfContainerRef) commentStore.registerPdfContainerRef(pdfContainerRef);
		return () => {
			commentStore.registerPdfContainerRef(null);
		};
	});

	// Initialize sidebar width from localStorage or center it
	$effect(() => {
		if (!containerWidth || sidebarWidthInitialized) return;

		const stored = localStorage.getItem('commentSidebarWidth');
		if (stored) {
			const parsedWidth = parseFloat(stored);
			const availableSpace = containerWidth - CONTROLS_WIDTH;
			const minCommentWidth = availableSpace * 0.2;
			const maxCommentWidth = availableSpace * 0.8;
			commentSidebarWidth = Math.max(minCommentWidth, Math.min(maxCommentWidth, parsedWidth));
		} else {
			// Center by default: 50% of available space (excluding controls)
			const availableSpace = containerWidth - CONTROLS_WIDTH;
			commentSidebarWidth = availableSpace * 0.5;
		}

		sidebarWidthInitialized = true;
	});

	// Save sidebar width to localStorage when it changes
	$effect(() => {
		if (sidebarWidthInitialized && commentSidebarWidth > 0) {
			localStorage.setItem('commentSidebarWidth', commentSidebarWidth.toString());
		}
	});

	// Calculate explicit widths for each section
	const CONTROLS_WIDTH = 320; // w-80 = 320px
	const DIVIDER_WIDTH = 4; // Actual divider width
	const PDF_PADDING = 32; // p-4 = 16px on each side

	const pdfContainerWidth = $derived.by(() => {
		if (!containerWidth) return 0;
		return Math.max(0, containerWidth - commentSidebarWidth - DIVIDER_WIDTH - CONTROLS_WIDTH);
	});

	const pdfContentWidth = $derived.by(() => {
		if (!pdfContainerWidth) return 0;
		return Math.max(0, pdfContainerWidth - PDF_PADDING);
	});

	// Auto-scale to exactly fit available width
	$effect(() => {
		if (!pageDataArray.length || !pdfContentWidth || pdfContentWidth === 0) return;

		const pdfBaseWidth = pageDataArray[0]?.width || 0;
		if (pdfBaseWidth === 0) return;

		const targetScale = pdfContentWidth / pdfBaseWidth;
		const MIN_SCALE = 0.1;
		const MAX_SCALE = 5.0;
		scale = Math.max(MIN_SCALE, Math.min(MAX_SCALE, targetScale));
	});

	// Handle scroll to detect current page
	function handleDocumentScroll() {
		if (!documentScrollRef || !pdfContainerRef) return;

		// Update scroll top state
		documentScrollTop = documentScrollRef.scrollTop;

		const scrollRect = documentScrollRef.getBoundingClientRect();
		const scrollCenter = scrollRect.top + scrollRect.height / 2;

		// Find which page is currently centered in viewport
		for (let i = 0; i < pageDataArray.length; i++) {
			const pageElement = commentStore.getPageElement(i + 1);
			if (pageElement) {
				const pageRect = pageElement.getBoundingClientRect();
				if (pageRect.top <= scrollCenter && pageRect.bottom >= scrollCenter) {
					const newPage = i + 1;
					if (currentPage !== newPage) {
						currentPage = newPage;
					}
					break;
				}
			}
		}
	}

	// Set up scroll handler for page detection
	$effect(() => {
		if (!documentScrollRef) return;

		documentScrollRef.addEventListener('scroll', handleDocumentScroll);

		return () => {
			documentScrollRef?.removeEventListener('scroll', handleDocumentScroll);
		};
	});

	// Interaction state
	let focusedCommentId = $state<number | null>(null);
	let hoveredCommentId = $state<number | null>(null);

	// Subscribe to comment store updates
	$effect(() => {
		const unsubscribe = commentStore.subscribe((comments) => {
			commentsWithAnnotation = comments;
		});
		return unsubscribe;
	});

	// Page navigation
	function scrollToPage(pageNum: number) {
		if (pageNum < 1 || pageNum > totalPages || !pdfContainerRef) return;

		const pageElement = commentStore.getPageElement(pageNum);
		if (pageElement && documentScrollRef) {
			const scrollTop =
				pageElement.getBoundingClientRect().top -
				documentScrollRef.getBoundingClientRect().top +
				documentScrollRef.scrollTop;
			documentScrollRef.scrollTo({ top: scrollTop, behavior: 'smooth' });
		}
	}

	let documentFile = $state<Blob | null>(null);
	const loadDocumentFile = async (): Promise<void> => {
		const result = await api.download(`/documents/${data.document.id}/file`);
		if (!result.success) {
			notification(result.error);
			return;
		}
		documentFile = result.data;
	};

	let wsUnsubscribe: (() => void) | null = null;

	onMount(async () => {
		// Initialize comment store
		await commentStore.initialize(data.document.id, data.sessionUser.id);

		// Load document file
		loadDocumentFile();

		// Connect to WebSocket for real-time updates
		await documentWebSocket.connect(data.document.id);

		// Subscribe to comment events from WebSocket
		wsUnsubscribe = documentWebSocket.onCommentEvent((event) => {
			commentStore.handleWebSocketEvent(event);
		});
	});

	onDestroy(() => {
		// Unsubscribe from WebSocket events
		if (wsUnsubscribe) {
			wsUnsubscribe();
		}

		// Clean up WebSocket connection
		documentWebSocket.disconnect();

		// Clear comment store
		commentStore.clear();
	});

	// ===== CORE LAYOUT ORCHESTRATION =====
	// This is the single point where we trigger layout recomputation.
	// Called whenever any layout-affecting dependency changes.
	$effect(() => {
		// Dependencies that affect layout
		void scale;
		void hoveredCommentId;
		void focusedCommentId;
		void isDragging;
		void documentScrollTop;
		void cssScaleFactor;
		void pageDataCacheVersion;

		// Must have required refs before computing
		if (!sidebarRef || !pdfContainerRef || !documentScrollRef) {
			return;
		}

		// Recompute layout synchronously (no debouncing for smooth scaling)
		commentStore.recomputeLayout({
			scale,
			sidebarRef,
			hoveredCommentId,
			focusedCommentId,
			isDragging
		});
	});
</script>

<!--Wrapper Flex Col-->
<section class="flex h-full w-full flex-col">
	<!--Header Section-->
	<section class="border-b border-text/10 bg-inset shadow-black/50 shadow-inner px-4 py-2">
		<h1 class="text-xl font-semibold text-text">{data.document.name}</h1>
	</section>

	<!--Content Section - Single Scroll Container-->
	<div class="flex-1 overflow-y-auto" bind:this={documentScrollRef}>
		<div
			class="relative flex min-h-full flex-row items-start"
			style="overflow-x: visible;"
			bind:this={containerRef}
		>
			{#if documentFile}
				<!--Controls Panel (Left Column)-->
				<div
					class="sticky top-4 shrink-0 self-start"
					style="width: {CONTROLS_WIDTH}px;"
				>
					<ControlsPanel
						bind:highlightColor
						commentsCount={commentsWithAnnotation.length}
						bind:scale
						{currentPage}
						{totalPages}
						onZoomIn={() => (scale = Math.min(scale + 0.25, 5))}
						onZoomOut={() => (scale = Math.max(scale - 0.25, 0.1))}
						onPagePrev={() => scrollToPage(currentPage - 1)}
						onPageNext={() => scrollToPage(currentPage + 1)}
					/>
				</div>

				<!--PDF Viewer (Center Column)-->
				<div
					class="shrink-0"
					style="width: {pdfContainerWidth}px;"
				>
					<PdfViewer
						pdfSource={documentFile}
						comments={commentsWithAnnotation}
						bind:scale
						bind:highlightColor
						bind:hoveredCommentId
						bind:focusedCommentId
						bind:totalPages
						bind:currentPage
						bind:pdfContainerRef
						bind:cssScaleFactor
					/>
				</div>

				<!--Resizable Divider-->
				<ResizableDivider onDragStart={handleDragStart} onDragMove={handleDragMove} bind:isDragging />

				<!--Comment Sidebar (Right Column)-->
				<div
					class="overflow-visible shrink-0"
					style="width: {commentSidebarWidth}px;"
					bind:this={sidebarRef}
				>
					<CommentSidebar
						{cssScaleFactor}
						{documentScrollTop}
						comments={commentsWithAnnotation}
						{isDragging}
						bind:hoveredCommentId
						bind:focusedCommentId
					/>
				</div>
			{:else}
				<div class="flex w-full items-center justify-center py-20">
					<div class="text-center">
						<div
							class="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-b-2 border-primary"
						></div>
						<p class="text-text/60">Loading document...</p>
					</div>
				</div>
			{/if}
		</div>
	</div>

	<!--Discussion Section-->
	<section>
		<!--TODO implement a discussion section with all comments that do not have annotation data and no parent (root comments)-->
	</section>
</section>
