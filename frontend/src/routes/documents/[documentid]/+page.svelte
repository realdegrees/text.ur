<script lang="ts">
	import Pdf from '$lib/components/pdf/Pdf.svelte';
	import { documentStore } from '$lib/runes/document.svelte.js';

	let { data } = $props();
	let { document, membership, group, rootComments, documentFile } = data;

	$effect(() => {
		documentStore.setRootComments(rootComments);
	});

</script>

<Pdf document={documentFile}></Pdf>
