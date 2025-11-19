<script lang="ts">
	import { api, type ApiGetResult } from '$api/client';
	import type { Paginated } from '$api/pagination.js';
	import type { CommentCreate, CommentRead, CommentUpdate } from '$api/types.js';
	import type { Annotation } from '$types/pdf';
	import { notification } from '$lib/stores/notificationStore';
	import PdfViewer from '$lib/components/pdf/PdfViewer.svelte';
	import CommentSidebar from '$lib/components/pdf/CommentSidebar.svelte';
	import ControlsPanel from '$lib/components/pdf/ControlsPanel.svelte';
	import { onMount } from 'svelte';

	let { data } = $props();
	let commentsWithAnnotation = $state<CommentRead[]>([]);

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

	// Recursively find and update a comment in a tree
	function updateCommentInTree(
		comments: CommentRead[],
		commentId: number,
		updater: (comment: CommentRead) => CommentRead
	): CommentRead[] {
		return comments.map((comment) => {
			if (comment.id === commentId) {
				return updater(comment);
			}
			if (comment.replies && comment.replies.length > 0) {
				return {
					...comment,
					replies: updateCommentInTree(comment.replies, commentId, updater)
				};
			}
			return comment;
		});
	}

	// Recursively find and delete a comment from a tree
	function deleteCommentFromTree(comments: CommentRead[], commentId: number): CommentRead[] {
		return comments
			.filter((comment) => comment.id !== commentId)
			.map((comment) => {
				if (comment.replies && comment.replies.length > 0) {
					return {
						...comment,
						replies: deleteCommentFromTree(comment.replies, commentId)
					};
				}
				return comment;
			});
	}

	// Recursively add a reply to a comment in a tree
	function addReplyToTree(
		comments: CommentRead[],
		parentId: number,
		newReply: CommentRead
	): CommentRead[] {
		return comments.map((comment) => {
			if (comment.id === parentId) {
				return {
					...comment,
					replies: [...(comment.replies || []), newReply]
				};
			}
			if (comment.replies && comment.replies.length > 0) {
				return {
					...comment,
					replies: addReplyToTree(comment.replies, parentId, newReply)
				};
			}
			return comment;
		});
	}

	// Handle comment deletion
	async function handleCommentDelete(commentId: number): Promise<void> {
		const deleteCommentResult = await api.delete(`/comments/${commentId}`);
		if (!deleteCommentResult.success) {
			notification(deleteCommentResult.error);
			return;
		}
		// Remove from local state (works for both top-level and nested)
		commentsWithAnnotation = deleteCommentFromTree(commentsWithAnnotation, commentId);
	}

	// Handle comment update
	async function handleCommentUpdate(commentId: number, updateData: CommentUpdate): Promise<void> {
		const updateResult = await api.update(`/comments/${commentId}`, updateData);
		if (!updateResult.success) {
			notification(updateResult.error);
			return;
		}
		// Update locally without refetching
		commentsWithAnnotation = updateCommentInTree(commentsWithAnnotation, commentId, (comment) => ({
			...comment,
			content: updateData.content ?? comment.content,
			visibility: updateData.visibility ?? comment.visibility,
			annotation: updateData.annotation ?? comment.annotation,
			updated_at: new Date().toISOString()
		}));
	}

	// Handle comment creation (replies)
	async function handleCommentCreate(commentData: CommentCreate): Promise<void> {
		const createResult = await api.post<CommentRead>('/comments', {
			...commentData,
			document_id: data.document.id,
			visibility: data.document.visibility
		});
		if (!createResult.success) {
			notification(createResult.error);
			return;
		}
		// Add reply to local state without refetching
		if (commentData.parent_id && createResult.data) {
			commentsWithAnnotation = addReplyToTree(
				commentsWithAnnotation,
				commentData.parent_id,
				createResult.data
			);
		} else if (createResult.data && !commentData.parent_id) {
			// Top-level comment (shouldn't happen in sidebar, but handle it)
			commentsWithAnnotation = [...commentsWithAnnotation, createResult.data];
		}
	}

	// Handle highlight creation
	async function handleHighlightCreate(annotation: Annotation): Promise<void> {
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
	}

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

	onMount(() => {
		fetchComments();
		loadDocumentFile();
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
						currentUserId={data.sessionUser.id}
						documentId={data.document.id}
						onCommentDelete={handleCommentDelete}
						onCommentUpdate={handleCommentUpdate}
						onCommentCreate={handleCommentCreate}
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
						onHighlightCreate={handleHighlightCreate}
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
