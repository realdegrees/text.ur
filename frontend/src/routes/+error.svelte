<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import LL from '$i18n/i18n-svelte';
</script>

<div class="flex h-full w-full flex-col items-center justify-center gap-4 p-8">
	<p class="text-8xl font-bold text-text/20">{page.status}</p>
	<p class="text-lg text-text/70">
		{page.error?.message ?? $LL.errorPage.unexpectedError()}
	</p>
	<button type="button" onclick={() => goto('/dashboard')} class="mt-4 btn-primary">
		{$LL.errorPage.goToDashboard()}
	</button>
</div>
