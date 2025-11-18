<script lang="ts">
	import { api, type ApiGetResult } from '$api/client';
	import type { Paginated } from '$api/pagination.js';
	import type { CommentCreate, CommentRead } from '$api/types.js';
	import { validatePermissions } from '$api/validatePermissions';
	import { notification } from '$lib/stores/notificationStore';
	import PdfViewer from '$lib/components/pdf.svelte';
	import DeleteIcon from '~icons/material-symbols/delete-outline';
	import { onMount } from 'svelte';

	let { data } = $props();

	let isAdmin = $derived.by((): boolean => {
		return validatePermissions(data.membership, ['administrator']);
	});
	let commentsWithAnnotation = $state<CommentRead[]>([]);

	// PDF viewer state (bound from PdfViewer component)
	let currentPage = $state(1);
	let textLayerHeight = $state(0);
	let textLayerWidth = $state(0);
	let toolbarHeight = $state(0);

	// Interaction state
	let focusedCommentId = $state<number | null>(null);
	let hoveredCommentId = $state<number | null>(null);
	let deleteConfirmId = $state<number | null>(null);

	// Check if a comment should be expanded
	function isCommentExpanded(commentId: number): boolean {
		return focusedCommentId === commentId || hoveredCommentId === commentId;
	}

	// Annotation type matching PdfViewer
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

	// Get comments for current page
	let currentPageComments = $derived.by(() => {
		return commentsWithAnnotation.filter((comment) => {
			const annotation = comment.annotation as unknown as Annotation;
			return annotation?.pageNumber === currentPage;
		});
	});

	// Calculate ideal vertical position for each comment based on its annotation
	function getIdealCommentTopPosition(comment: CommentRead): number {
		const annotation = comment.annotation as unknown as Annotation;
		if (!annotation || !annotation.boundingBoxes || annotation.boundingBoxes.length === 0) {
			return 0;
		}

		// Find the topmost bounding box
		const topBox = annotation.boundingBoxes.reduce((prev, curr) => {
			return curr.y < prev.y ? curr : prev;
		});

		// Convert normalized position to pixels (relative to text layer)
		const topPositionPx = topBox.y * textLayerHeight;

		// Add toolbar height offset
		return topPositionPx + toolbarHeight;
	}

	// Get the right edge position of the highlight (for line connection)
	function getHighlightRightEdge(comment: CommentRead): number {
		const annotation = comment.annotation as unknown as Annotation;
		if (!annotation || !annotation.boundingBoxes || annotation.boundingBoxes.length === 0) {
			return 0;
		}

		// Find the rightmost bounding box
		const rightBox = annotation.boundingBoxes.reduce((prev, curr) => {
			const prevRight = prev.x + prev.width;
			const currRight = curr.x + curr.width;
			return currRight > prevRight ? curr : prev;
		});

		// Convert normalized position to pixels
		return (rightBox.x + rightBox.width) * textLayerWidth;
	}

	// Calculate non-overlapping positions for all comments
	interface PositionedComment {
		comment: CommentRead;
		idealTop: number;
		actualTop: number;
		rightEdge: number;
	}

	let positionedComments = $derived.by((): PositionedComment[] => {
		const COMMENT_HEIGHT = 60; // Approximate height of each comment
		const MIN_GAP = 8; // Minimum gap between comments

		// Sort by ideal position
		const sorted = currentPageComments.map(comment => ({
			comment,
			idealTop: getIdealCommentTopPosition(comment),
			actualTop: 0,
			rightEdge: getHighlightRightEdge(comment)
		})).sort((a, b) => a.idealTop - b.idealTop);

		// Apply overlap protection
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
<section class="flex h-full w-full flex-col gap-4">
	<!--Header Section-->
	<section></section>

	<!--Content Section-->
	<section class="flex h-full w-full flex-row gap-0">
		<!--Comments Section-->
		<section class="relative flex-1 overflow-y-auto bg-gray-50 pr-4">
			<div class="relative h-full">
				{#each positionedComments as { comment, actualTop, idealTop, rightEdge } (comment.id)}
					{@const annotation = comment.annotation as unknown as Annotation}
					{@const expanded = isCommentExpanded(comment.id)}
					{@const showDeleteConfirm = deleteConfirmId === comment.id}

					<!-- Connection line from highlight to comment (only when expanded) -->
					{#if expanded}
						<svg
							class="pointer-events-none absolute left-0 top-0"
							style:width="100%"
							style:height="{Math.max(actualTop + 30, idealTop + 30)}px"
						>
							<line
								x1="100%"
								y1="{idealTop + 12}px"
								x2="calc(100% - 12px)"
								y2="{actualTop + 12}px"
								stroke={annotation.color}
								stroke-width="1.5"
								stroke-opacity="0.5"
							/>
						</svg>
					{/if}

					{#if expanded}
						<!-- Expanded comment card -->
						<div
							data-comment-id={comment.id}
							class="absolute left-0 right-4 rounded border-l-4 bg-white px-3 py-2 shadow-md transition-all duration-200"
							style:top="{actualTop}px"
							style:border-left-color={annotation.color}
							onmouseenter={() => hoveredCommentId = comment.id}
							onmouseleave={() => hoveredCommentId = null}
							onclick={(e) => {
								e.stopPropagation();
								focusedCommentId = focusedCommentId === comment.id ? null : comment.id;
							}}
							role="button"
							tabindex="0"
						>
							{#if showDeleteConfirm}
								<!-- Delete confirmation -->
								<div class="flex flex-col gap-2" onclick={(e) => e.stopPropagation()}>
									<p class="text-xs font-semibold text-red-600">Delete this comment?</p>
									<div class="flex gap-2">
										<button
											onclick={async (e) => {
												e.stopPropagation();
												const deleteCommentResult = await api.delete(`/comments/${comment.id}`);
												if (!deleteCommentResult.success) {
													notification(deleteCommentResult.error);
													return;
												}
												commentsWithAnnotation = commentsWithAnnotation.filter(c => c.id !== comment.id);
												focusedCommentId = null;
												hoveredCommentId = null;
												deleteConfirmId = null;
											}}
											class="rounded bg-red-500/20 px-2 py-1 text-xs font-semibold text-red-600 hover:bg-red-500/30"
										>
											Delete
										</button>
										<button
											onclick={(e) => {
												e.stopPropagation();
												deleteConfirmId = null;
											}}
											class="rounded bg-gray-200 px-2 py-1 text-xs font-semibold text-gray-700 hover:bg-gray-300"
										>
											Cancel
										</button>
									</div>
								</div>
							{:else}
								<!-- Normal comment display -->
								<div class="mb-1 flex items-center justify-between">
									<span class="text-xs font-medium text-gray-600">
										{comment.user?.username ?? 'Anonymous'}
									</span>
									<button
										onclick={(e) => {
											e.stopPropagation();
											deleteConfirmId = comment.id;
										}}
										class="text-gray-400 hover:text-red-600"
										aria-label="Delete comment"
									>
										<DeleteIcon class="h-4 w-4" />
									</button>
								</div>
								{#if comment.content}
									<p class="text-sm text-gray-800 leading-snug">{comment.content}</p>
								{:else}
									<p class="text-xs italic text-gray-400">No comment added</p>
								{/if}
							{/if}
						</div>
					{:else}
						<!-- Collapsed badge indicator -->
						<div
							data-comment-id={comment.id}
							class="absolute right-4 rounded-full px-2 py-1 shadow-sm transition-all duration-200 cursor-pointer hover:shadow-md"
							style:top="{actualTop}px"
							style:background-color={annotation.color}
							onmouseenter={() => hoveredCommentId = comment.id}
							onmouseleave={() => hoveredCommentId = null}
							onclick={(e) => {
								e.stopPropagation();
								focusedCommentId = comment.id;
							}}
							role="button"
							tabindex="0"
						>
							<span class="text-xs font-medium text-gray-800">
								{comment.user?.username ?? 'Anonymous'}
							</span>
						</div>
					{/if}
				{/each}
			</div>
		</section>

		<!--PDF Section-->
		<section class="h-full w-fit flex-shrink-0">
			<!-- Inline PDF viewer component. Uses `annotationsToShow` (transformed from `commentsWithAnnotation`). -->
			{#if documentFile}
				<PdfViewer
					pdfSource={documentFile}
					comments={commentsWithAnnotation}
					bind:currentPage
					bind:textLayerHeight
					bind:textLayerWidth
					bind:toolbarHeight
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
						
						commentsWithAnnotation = [
							...commentsWithAnnotation,
							commentCreateResult.data
						];
					}}
				/>
			{:else}
				<p>Loading document...</p>
			{/if}
		</section>

		<!--Tools & Meta Section-->
		<section class="flex grow flex-col items-start justify-start gap-4">
			<!--Toolbar Section-->
			<section></section>

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
		</section>
	</section>

	<!--Discussion Section-->
	<section>
		<!--TODO implement a discussion section with all comments that do not have annotation data and no parent (root comments)-->
	</section>
</section>
