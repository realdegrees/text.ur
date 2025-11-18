<script lang="ts">
	import { api, type ApiGetResult } from '$api/client';
	import type { Paginated } from '$api/pagination.js';
	import type { CommentCreate, CommentRead } from '$api/types.js';
	import { validatePermissions } from '$api/validatePermissions';
	import { notification } from '$lib/stores/notificationStore';
	import PdfViewer from '$lib/components/pdf.svelte';
	import PdfToolbar from '$lib/components/pdf/PdfToolbar.svelte';
	import CommentsList from '$lib/components/comments/CommentsList.svelte';
	import { onMount } from 'svelte';

	let { data } = $props();

	let isAdmin = $derived.by((): boolean => {
		return validatePermissions(data.membership, ['administrator']);
	});
	let commentsWithAnnotation = $state<CommentRead[]>([]);

	// PDF viewer state
	let pdfViewerRef: PdfViewer | null = $state(null);
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
	let deleteConfirmId = $state<number | null>(null);


	// Handle comment deletion
	async function handleCommentDelete(commentId: number): Promise<void> {
		const deleteCommentResult = await api.delete(`/comments/${commentId}`);
		if (!deleteCommentResult.success) {
			notification(deleteCommentResult.error);
			return;
		}
		commentsWithAnnotation = commentsWithAnnotation.filter((c) => c.id !== commentId);
	}

	const fetchComments = async (): Promise<void> => {
		const limit = 50;
		let offset = 0;
		let result: ApiGetResult<Paginated<CommentRead, 'document'>>;

		while (true) {
			result = await api.get<Paginated<CommentRead, 'document'>>(
				`/comments?offset=${offset}&limit=${limit}`,
				{
					filters: [
						{
							field: 'parent_id',
							operator: 'exists',
							value: 'false'
						},
						{
							field: 'annotation',
							operator: 'exists',
							value: 'true'
						},
						{
							field: 'document_id',
							operator: '==',
							value: data.document.id.toString()
						}
					]
				}
			);

			if (!result.success) {
				notification(result.error);
				return;
			}

			if (result.data.total <= result.data.offset + result.data.limit) {
				commentsWithAnnotation = [...commentsWithAnnotation, ...result.data.data];
				break;
			} else {
				commentsWithAnnotation = [...commentsWithAnnotation, ...result.data.data];
				offset += limit;
			}
		}
	};
	let documentFile = $state<Blob | null>(null);
	const loadDocumentFile = async (): Promise<void> => {
		const result = await api.download(`/documents/${data.document.id}/file`);
		if (!result.success) {
			notification(result.error);
			return;
		}
		documentFile = result.data;
	};

	// Handle click outside to clear focus
	function handleDocumentClick(event: MouseEvent) {
		const target = event.target as HTMLElement;

		// Check if click is on a comment card, badge, or highlight
		const isCommentClick = target.closest('[data-comment-id]');
		const isHighlightClick = target.closest('.annotation-group');

		// If not clicking on a comment or highlight, clear focus
		if (!isCommentClick && !isHighlightClick) {
			focusedCommentId = null;
			deleteConfirmId = null;
		}
	}

	onMount(() => {
		fetchComments();
		loadDocumentFile();

		// Add global click listener for focus management
		document.addEventListener('click', handleDocumentClick);

		return () => {
			document.removeEventListener('click', handleDocumentClick);
		};
	});
</script>

<!--Wrapper Flex Col-->
<section class="flex h-full w-full flex-col gap-1">
	<!--Header Section-->
	<section></section>

	<!--Content Section - Single Scroll Container-->
	<div class="flex-1 overflow-y-auto" bind:this={documentScrollRef}>
		<div class="flex min-h-full flex-row items-start">
			<!--Comments Section-->
			<div class="relative flex-1 bg-gray-50 pr-4">
				<CommentsList
					comments={commentsWithAnnotation}
					documentScrollRef={documentScrollRef}
					pdfContainerRef={pdfContainerRef}
					{pageDataArray}
					bind:focusedCommentId
					bind:hoveredCommentId
					bind:deleteConfirmId
					onDelete={handleCommentDelete}
				/>
			</div>

			<!--PDF Section-->
			<div class="flex shrink-0 items-start justify-center">
				<!-- Inline PDF viewer component. Uses `annotationsToShow` (transformed from `commentsWithAnnotation`). -->
				{#if documentFile}
					<PdfViewer
						bind:this={pdfViewerRef}
						bind:pdfContainerRef
						pdfSource={documentFile}
						comments={commentsWithAnnotation}
						bind:currentPage
						bind:scale
						bind:highlightColor
						bind:totalPages
						bind:pageDataArray
						bind:hoveredCommentId
						bind:focusedCommentId
						onAnnotationCreate={async (annotation) => {
							const commentCreateResult = await api.post<CommentRead>('/comments', {
								document_id: data.document.id,
								annotation: annotation as unknown as { [k: string]: unknown },
								visibility: data.document.visibility
							} satisfies CommentCreate);
							if (!commentCreateResult.success) {
								notification(commentCreateResult.error);
								return;
							}

							commentsWithAnnotation = [...commentsWithAnnotation, commentCreateResult.data];
						}}
					/>
				{:else}
					<p>Loading document...</p>
				{/if}
			</div>

			<!--Tools & Meta Section-->
			<div class="flex flex-1 flex-col items-start justify-start gap-4">
				<!--Toolbar Section-->
				<section class="w-full">
					<PdfToolbar bind:highlightColor commentsCount={commentsWithAnnotation.length} />
				</section>

				<!--Document Settings Section-->
				{#if isAdmin}
					<section>
						<!--TODO add document settings like visibility mode for admins only-->
					</section>
				{/if}

				<!--Active Users Section-->
				<section>
					<!--TODO show users currently connected to the document websocket-->
				</section>

				<!--TODO maybe add more stuff here-->
			</div>
		</div>
	</div>

	<!--Discussion Section-->
	<section>
		<!--TODO implement a discussion section with all comments that do not have annotation data and no parent (root comments)-->
	</section>
</section>
