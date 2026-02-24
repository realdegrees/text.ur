<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
</script>

<div class="flex h-full w-full flex-col items-center justify-center gap-4 p-8">
	<p class="text-8xl font-bold text-text/20">{page.status}</p>
	<p class="text-lg text-text/70">
		{page.error?.message ?? 'An unexpected error occurred'}
	</p>
	<button type="button" onclick={() => goto('/dashboard')} class="mt-4 btn-primary">
		Go to Dashboard
	</button>
</div>
