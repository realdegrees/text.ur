<script lang="ts">
	import ImprintEn from '$lib/legal/imprint/en.svx';
	import ImprintDe from '$lib/legal/imprint/de.svx';
	import language from '$lib/stores/language.svelte';
</script>

<div class="mx-auto prose max-w-4xl overflow-y-auto p-8">
	{#if language.locale === 'de'}
		<ImprintDe />
	{:else}
		<ImprintEn />
	{/if}
</div>
