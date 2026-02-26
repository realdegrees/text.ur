<script lang="ts">
	import Field from '$lib/components/advancedInput.svelte';
	import InfoBanner from '$lib/components/InfoBanner.svelte';
	import Loading from '~icons/svg-spinners/90-ring-with-bg';
	import { api } from '$api/client';
	import { resolveErrorMessage } from '$lib/util/errorMessage';
	import LL from '$i18n/i18n-svelte';

	let { onSuccess }: { onSuccess: () => void } = $props();

	let username = $state('');
	let email = $state('');
	let firstName = $state('');
	let lastName = $state('');
	let password = $state('');
	let confirmPassword = $state('');
	let isLoading = $state(false);
	let errorMessage = $state<string | null>(null);
	let successMessage = $state<string | null>(null);

	async function handleRegister(e: Event) {
		e.preventDefault();
		isLoading = true;
		errorMessage = null;
		successMessage = null;

		if (password !== confirmPassword) {
			errorMessage = $LL.passwordReset.passwordsDoNotMatch();
			isLoading = false;
			return;
		}

		try {
			const result = await api.post('/register', {
				username,
				email,
				password,
				first_name: firstName || undefined,
				last_name: lastName || undefined
			});

			if (!result.success) {
				errorMessage = resolveErrorMessage(result.error);
				return;
			}

			successMessage = $LL.loginPage.registrationSuccess();
			onSuccess();
		} finally {
			isLoading = false;
		}
	}
</script>

<form onsubmit={handleRegister} class="flex flex-col gap-4">
	{#if errorMessage}
		<InfoBanner variant="error">{errorMessage}</InfoBanner>
	{/if}
	{#if successMessage}
		<InfoBanner variant="info">{successMessage}</InfoBanner>
	{/if}
	<Field bind:value={username} label="Username" required />
	<Field bind:value={email} label="Email" required />
	<div class="flex w-full flex-row gap-4">
		<Field bind:value={firstName} label="First Name" />
		<Field bind:value={lastName} label="Last Name" />
	</div>

	<Field bind:value={password} label="Password" hidden required />
	<Field bind:value={confirmPassword} label="Confirm Password" hidden required />
	<button type="submit" class="w-full btn-primary py-3" disabled={isLoading}>
		{#if isLoading}
			<Loading />
		{:else}
			Register
		{/if}
	</button>
</form>
