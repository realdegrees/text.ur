<script lang="ts">
	import Pdf from '$lib/components/pdf/Pdf.svelte';
	import { documentStore } from '$lib/runes/document.svelte.js';
	import { sessionStore } from '$lib/runes/session.svelte.js';
	import { documentWebSocket } from '$lib/stores/documentWebSocket';

	let { data } = $props();
	let { document, membership, rootComments, documentFile } = data;

	// Initialize session and document stores (reactive to data changes)
	$effect(() => {
		sessionStore.currentUser = data.sessionUser;
		sessionStore.currentMembership = membership;
		documentStore.setDocument(document);
		documentStore.setRootComments(rootComments);
	});

	// WebSocket connection lifecycle (separate effect with cleanup)
	$effect(() => {
		let wsUnsubscribe: (() => void) | null = null;
		let vmUnsubscribe: (() => void) | null = null;

		// Connect to WebSocket for real-time comment updates
		documentWebSocket.connect(document.id.toString()).then(() => {
			wsUnsubscribe = documentWebSocket.onCommentEvent((event) => {
				documentStore.handleWebSocketEvent(event);
			});
			vmUnsubscribe = documentWebSocket.onViewModeChanged((ev) => documentStore.handleWebSocketEvent(ev as any));
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
	<Pdf document={documentFile} />
</div>
