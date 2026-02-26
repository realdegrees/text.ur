<script lang="ts">
	import Field from '$lib/components/advancedInput.svelte';
	import InfoBanner from '$lib/components/InfoBanner.svelte';
	import Loading from '~icons/svg-spinners/90-ring-with-bg';
	import { api } from '$api/client';
	import { resolveErrorMessage } from '$lib/util/errorMessage';
	import LL from '$i18n/i18n-svelte';

	let email = $state('');
	let isLoading = $state(false);
	let errorMessage = $state<string | null>(null);
	let successMessage = $state<string | null>(null);

	async function handleResetRequest(e: Event) {
		e.preventDefault();
		isLoading = true;
		errorMessage = null;
		successMessage = null;

		try {
			const result = await api.post('/login/reset', { email });

			if (!result.success) {
				errorMessage = resolveErrorMessage(result.error);
				return;
			}

			successMessage = $LL.passwordReset.resetSent();
			email = ''; // Clear the form
		} finally {
			isLoading = false;
		}
	}
</script>

<div class="mt-20 flex h-fit w-full justify-center">
	<div class="w-full max-w-md overflow-hidden rounded-lg bg-inset p-8 shadow-lg">
		<h1 class="mb-2 text-2xl font-bold">{$LL.passwordReset.requestTitle()}</h1>
		<p class="mb-6 text-muted">{$LL.passwordReset.requestDescription()}</p>

		<form onsubmit={handleResetRequest} class="flex flex-col gap-4">
			{#if errorMessage}
				<InfoBanner variant="error">{errorMessage}</InfoBanner>
			{/if}
			{#if successMessage}
				<InfoBanner variant="info">{successMessage}</InfoBanner>
			{/if}
			<Field bind:value={email} label={$LL.passwordReset.emailLabel()} required />
			<button type="submit" class="w-full btn-primary py-3" disabled={isLoading}>
				{#if isLoading}
					<Loading />
				{:else}
					{$LL.passwordReset.sendResetLink()}
				{/if}
			</button>
		</form>

		<div class="mt-4 text-center text-sm">
			<a href="/login" class="text-primary hover:underline">{$LL.passwordReset.backToLogin()}</a>
		</div>
	</div>
</div>
