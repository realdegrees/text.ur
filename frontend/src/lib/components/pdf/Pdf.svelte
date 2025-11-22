<script lang="ts">
  import type { PDFSlick } from '@pdfslick/core';
  import { onDestroy, onMount } from 'svelte';
    import "@pdfslick/core/dist/pdf_viewer.css";

  let container: HTMLDivElement | null = $state(null);
  let pdfSlick: PDFSlick | null = $state(null);
  let unsubscribe: (() => void) | null = $state(null);

  let pageNumber = $state(1);
  let numPages = $state(0);

  let { document: pdfData }: { document: ArrayBuffer } = $props();

  

  const initialize = async () => {
    if (!container) return;
    /**
     * This is all happening on client side, so we'll make sure we only load it there
     */
    const { create, PDFSlick } = await import('@pdfslick/core');

    /**
     * Create the PDF Slick store 
     */
    const store = create();

    pdfSlick = new PDFSlick({
      container,
      store,
      options: {
        scaleValue: 'page-fit'
      }
    });

    /**
     * Load the PDF document
     */
    pdfSlick.loadDocument(pdfData);
    store.setState({ pdfSlick });

    /**
     * Subscribe to state changes, and keep values of interest as reactive Svelte vars, 
     * (or alternatively we could hook these or entire PDF state into a Svelte store)
     * 
     * Also keep reference of the unsubscribe function we call on component destroy
     */
    unsubscribe = store.subscribe((s) => {
      pageNumber = s.pageNumber;
      numPages = s.numPages;
      console.log('PDFSlickState', s); // ! This PDFSlickState object holds a lot of info like zoom , curent page, total pages, etc. and updates on changes reactivley
    });
  }

  onMount(initialize);
  onDestroy(() => unsubscribe?.())
</script>

<!-- ... -->

<div class="absolute inset-0 bg-slate-200/70 pdfSlick">

  <div class="flex-1 relative h-full" id="container">
    <!--
      The important part —
      we use the reference to this `container` when creating PDF Slick instance above
    -->
    <div id="viewerContainer" class="pdfSlickContainer absolute inset-0 overflow-auto" bind:this={container}>
      <div id="viewer" class="pdfSlickViewer pdfViewer"></div>
    </div>
  </div>

  <!-- ... -->

  <!-- Use `pdfSlick`, `pageNumber` and `numPages` to create PDF pagination -->
  <div class="flex justify-center">
    <button
      onclick={() => pdfSlick?.gotoPage(Math.max(pageNumber - 1, 1))}
      disabled={pageNumber <= 1}
		>
      Show Previous Page
    </button>
    <button
      onclick={() =>  pdfSlick?.gotoPage(Math.min(pageNumber + 1, numPages))}
      disabled={pageNumber >= numPages}
    >
      Show Next Page
    </button>
  </div>

</div>