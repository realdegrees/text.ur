<script lang="ts">
	import Pdf from '$lib/components/pdf/Pdf.svelte';
	import { documentStore } from '$lib/runes/document.svelte.js';
	import { documentWebSocket } from '$lib/stores/documentWebSocket';

	let { data } = $props();

	// Extract document ID to prevent WebSocket effect from re-running on data refresh
	// (invalidateAll updates data object but ID stays the same)
	let documentId = $derived(data.document.id);

	// Initialize session and document stores (reactive to data changes)
	// Use data.X directly so the effect re-runs when invalidateAll() updates data
	$effect(() => {
		documentStore.setDocument(data.document);
		documentStore.setRootComments(data.rootComments);
	});

	// WebSocket connection lifecycle (separate effect with cleanup)
	// Only re-runs when documentId actually changes, not on every data refresh
	$effect(() => {
		const docId = documentId; // Track only the ID
		let wsUnsubscribe: (() => void) | null = null;
		let vmUnsubscribe: (() => void) | null = null;

		// Connect to WebSocket for real-time comment updates
		documentWebSocket.connect(docId.toString()).then(() => {
			wsUnsubscribe = documentWebSocket.onCommentEvent((event) => {
				documentStore.handleWebSocketEvent(event);
			});
			vmUnsubscribe = documentWebSocket.onViewModeChanged((ev) =>
				documentStore.handleWebSocketEvent(ev as any)
			);
		});

		// Cleanup when effect re-runs or component unmounts
		return () => {
			wsUnsubscribe?.();
			vmUnsubscribe?.();
			documentWebSocket.disconnect();
			documentStore.clearAllInteractionState();
		};
	});
</script>

<div class="h-full w-full">
	<Pdf document={data.documentFile} />
</div>
