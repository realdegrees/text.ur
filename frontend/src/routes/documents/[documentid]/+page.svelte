<script lang="ts">
	import { api } from '$api/client';
	import { notification } from '$lib/stores/notificationStore';
	import { commentStore } from '$lib/stores/commentStore';
	import PdfViewer from '$lib/components/pdf/PdfViewer.svelte';
	import CommentSidebar from '$lib/components/pdf/CommentSidebar.svelte';
	import ControlsPanel from '$lib/components/pdf/ControlsPanel.svelte';
	import { onMount, onDestroy } from 'svelte';

	let { data } = $props();
	let commentsWithAnnotation = $state($commentStore);

	// PDF viewer state
	let documentScrollRef: HTMLDivElement | null = $state(null);
	let pdfContainerRef: HTMLDivElement | null = $state(null);
	let currentPage = $state(1);
	let totalPages = $state(0);
	let scale = $state(1.5);
	let highlightColor = $state('#FFFF00');
	let pageDataArray = $state<Array<{ pageNumber: number; width: number; height: number }>>([]);

	// Handle scroll to detect current page
	function handleDocumentScroll() {
		if (!documentScrollRef || !pdfContainerRef) return;

		const scrollRect = documentScrollRef.getBoundingClientRect();
		const scrollCenter = scrollRect.top + scrollRect.height / 2;

		// Find which page is currently centered in viewport
		for (let i = 0; i < pageDataArray.length; i++) {
			const pageElement = pdfContainerRef.querySelector(`[data-page-number="${i + 1}"]`);
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

		const pageElement = pdfContainerRef.querySelector(`[data-page-number="${pageNum}"]`);
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

	onMount(async () => {
		await commentStore.initialize(data.document.id, data.sessionUser.id);
		loadDocumentFile();
	});

	onDestroy(() => {
		commentStore.clear();
	});
</script>

<!--Wrapper Flex Col-->
<section class="flex h-full w-full flex-col gap-1">
	<!--Header Section-->
	<section class="border-b border-gray-200 bg-white px-4 py-2">
		<h1 class="text-xl font-semibold text-gray-800">{data.document.name}</h1>
	</section>

	<!--Content Section - Single Scroll Container-->
	<div class="flex-1 overflow-y-auto" bind:this={documentScrollRef}>
		<div
			class="relative flex min-h-full flex-row items-start justify-center"
			style="overflow-x: visible;"
		>
			{#if documentFile}
				<!--Comment Sidebar (Left Column)-->
				<div class="flex-1 overflow-visible">
					<CommentSidebar
						comments={commentsWithAnnotation}
						{pageDataArray}
						{pdfContainerRef}
						scrollContainerRef={documentScrollRef}
						bind:hoveredCommentId
						bind:focusedCommentId
					/>
				</div>

				<!--PDF Viewer (Center Column)-->
				<div class="shrink-0">
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
						onPageDataUpdate={(data) => (pageDataArray = data)}
					/>
				</div>

				<!--Controls Panel (Right Column)-->
				<div class="flex-1">
					<ControlsPanel
						bind:highlightColor
						commentsCount={commentsWithAnnotation.length}
						bind:scale
						{currentPage}
						{totalPages}
						onZoomIn={() => (scale = Math.min(scale + 0.25, 3))}
						onZoomOut={() => (scale = Math.max(scale - 0.25, 0.5))}
						onPagePrev={() => scrollToPage(currentPage - 1)}
						onPageNext={() => scrollToPage(currentPage + 1)}
					/>
				</div>
			{:else}
				<div class="flex w-full items-center justify-center py-20">
					<div class="text-center">
						<div
							class="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-b-2 border-blue-600"
						></div>
						<p class="text-gray-600">Loading document...</p>
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
