<script lang="ts">
	import { api, type ApiGetResult } from '$api/client';
	import type { Paginated } from '$api/pagination.js';
	import type { CommentCreate, CommentRead } from '$api/types.js';
	import { validatePermissions } from '$api/validatePermissions';
	import { notification } from '$lib/stores/notificationStore';
	import PdfViewer from '$lib/components/pdf.svelte';
	import { onMount } from 'svelte';

	let { data } = $props();

	let isAdmin = $derived.by((): boolean => {
		return validatePermissions(data.membership, ['administrator']);
	});
	let commentsWithAnnotation = $state<CommentRead[]>([]);

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
<section class="flex h-full w-full flex-col gap-4">
	<!--Header Section-->
	<section></section>

	<!--Content Section-->
	<section class="flex h-full w-full flex-row">
		<!--Comments Section-->
		<section class="grow"></section>

		<!--PDF Section-->
		<section class="h-full w-fit">
			<!-- Inline PDF viewer component. Uses `annotationsToShow` (transformed from `commentsWithAnnotation`). -->
			{#if documentFile}
				<PdfViewer
					pdfSource={documentFile}
					comments={commentsWithAnnotation}
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
					onAnnotationSelect={async (comment) => {
						// Placeholder: Delete Comment
						const deleteCommentResult = await api.delete(`/comments/${comment.id}`);
						if (!deleteCommentResult.success) {
							notification(deleteCommentResult.error);
							return;
						}

						commentsWithAnnotation = commentsWithAnnotation.filter(c => c.id !== comment.id);
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
