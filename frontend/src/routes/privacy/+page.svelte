<script lang="ts">
	import PrivacyEn from '$lib/legal/privacy/en.svx';
	import PrivacyDe from '$lib/legal/privacy/de.svx';
	import language from '$lib/stores/language.svelte';
</script>

<div class="mx-auto prose max-w-4xl overflow-y-auto p-8">
	{#if language.locale === 'de'}
		<PrivacyDe />
	{:else}
		<PrivacyEn />
	{/if}
</div>
