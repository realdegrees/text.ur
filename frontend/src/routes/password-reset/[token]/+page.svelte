<script lang="ts">
	import Field from '$lib/components/advancedInput.svelte';
	import InfoBanner from '$lib/components/InfoBanner.svelte';
	import Loading from '~icons/svg-spinners/90-ring-with-bg';
	import { api } from '$api/client';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import LL from '$i18n/i18n-svelte';

	// Extract token from URL params before clearing it
	const token = $page.params.token;

	// Clear token from URL immediately for security (prevents it staying in browser history)
	onMount(() => {
		if (typeof window !== 'undefined') {
			window.history.replaceState({}, '', '/password-reset');
		}
	});

	let password = $state('');
	let confirmPassword = $state('');
	let isLoading = $state(false);
	let errorMessage = $state<string | null>(null);

	async function handlePasswordReset(e: Event) {
		e.preventDefault();
		isLoading = true;
		errorMessage = null;

		if (password !== confirmPassword) {
			errorMessage = $LL.passwordReset.passwordsDoNotMatch();
			isLoading = false;
			return;
		}

		if (password.length < 8) {
			errorMessage = $LL.passwordReset.passwordMinLength();
			isLoading = false;
			return;
		}

		try {
			const result = await api.update(`/login/reset/verify/${token}`, { password });

			if (!result.success) {
				errorMessage = result.error.detail || $LL.passwordReset.resetFailedExpired();
				return;
			}

			// Success! Redirect to login with a success message
			goto('/login?reset=success');
		} finally {
			isLoading = false;
		}
	}
</script>

<div class="mt-20 flex h-fit w-full justify-center">
	<div class="w-full max-w-md overflow-hidden rounded-lg bg-inset p-8 shadow-lg">
		<h1 class="mb-2 text-2xl font-bold">{$LL.passwordReset.setNewPassword()}</h1>
		<p class="mb-6 text-muted">{$LL.passwordReset.setNewPasswordDescription()}</p>

		<form onsubmit={handlePasswordReset} class="flex flex-col gap-4">
			{#if errorMessage}
				<InfoBanner variant="error">{errorMessage}</InfoBanner>
			{/if}
			<Field bind:value={password} label={$LL.passwordReset.newPasswordLabel()} hidden required />
			<Field
				bind:value={confirmPassword}
				label={$LL.passwordReset.confirmPasswordLabel()}
				hidden
				required
			/>
			<button type="submit" class="w-full btn-primary py-3" disabled={isLoading}>
				{#if isLoading}
					<Loading />
				{:else}
					{$LL.passwordReset.resetButton()}
				{/if}
			</button>
		</form>

		<div class="mt-4 text-center text-sm">
			<a href="/login" class="text-primary hover:underline">{$LL.passwordReset.backToLogin()}</a>
		</div>
	</div>
</div>
