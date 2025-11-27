<script lang="ts">
	import { LL } from '$i18n/i18n-svelte';
	import Loading from '~icons/svg-spinners/90-ring-with-bg';
	import { Tween } from 'svelte/motion';
	import { cubicOut } from 'svelte/easing';
	import Field from '$lib/components/advancedInput.svelte';
	import { page } from '$app/state';
	import { api } from '$api/client';
	import { goto } from '$app/navigation';

	let isRegistering = $state(false);
	let isLoading = $state(false);
	let errorMessage = $state<string | null>(null);
	let successMessage = $state<string | null>(null);

	// Form fields for login
	let loginUsername = $state('');
	let loginPassword = $state('');

	// Form fields for registration
	let registerUsername = $state('');
	let registerEmail = $state('');
	let registerFirstName = $state('');
	let registerLastName = $state('');
	let registerPassword = $state('');
	let registerConfirmPassword = $state('');

	const toggleMode = () => {
		isRegistering = !isRegistering;
		errorMessage = null;
		successMessage = null;
	};

	const handleSubmit = async (e: Event) => {
		e.preventDefault();
		errorMessage = null;
		successMessage = null;
		isLoading = true;

		try {
			if (isRegistering) {
				// Handle registration
				if (!registerUsername || !registerEmail || !registerPassword) {
					errorMessage = 'Username, email, and password are required';
					return;
				}

				if (registerPassword !== registerConfirmPassword) {
					errorMessage = 'Passwords do not match';
					return;
				}

				const result = await api.post('/register', {
					username: registerUsername,
					email: registerEmail,
					password: registerPassword,
					first_name: registerFirstName || undefined,
					last_name: registerLastName || undefined
				});

				if (!result.success) {
					errorMessage = result.error.detail || 'Registration failed';
					return;
				}

				successMessage = 'Registration successful! Please check your email to verify your account.';
			} else {
				// Handle login
				if (!loginUsername || !loginPassword) {
					errorMessage = 'Username/Email and password are required';
					return;
				}

				const formData = new FormData();
				formData.append('username', loginUsername);
				formData.append('password', loginPassword);

				const result = await api.post('/login', formData);

				if (!result.success) {
					errorMessage = result.error.detail || 'Invalid username/email or password';
					return;
				}

				// Check for redirect parameter
				const redirectTo = page.url.searchParams.get('redirect') || '/';
				await goto(redirectTo);
			}
		} finally {
			isLoading = false;
		}
	};

	let innerEl: HTMLDivElement;
	const height = new Tween(0, { duration: 250, easing: cubicOut });

	$effect(() => {
		if (innerEl) height.set(innerEl.offsetHeight);
	});
</script>

<div class="flex h-full w-full items-center justify-center p-4">
	<div
		class="w-full max-w-md overflow-hidden rounded-lg bg-inset p-8 shadow-lg"
		style="height: {height}px"
	>
		<div bind:this={innerEl}>
			<h1 class="mb-6 text-center text-3xl font-bold text-text">
				{isRegistering ? $LL.register() : $LL.login()}
			</h1>

			{#if errorMessage}
				<div
					class="mb-4 rounded border border-red-300 bg-red-100 p-3 text-red-700 dark:border-red-700 dark:bg-red-900/30 dark:text-red-300"
				>
					{errorMessage}
				</div>
			{/if}

			{#if successMessage}
				<div
					class="mb-4 rounded border border-green-300 bg-green-100 p-3 text-green-700 dark:border-green-700 dark:bg-green-900/30 dark:text-green-300"
				>
					{successMessage}
				</div>
			{/if}

			<form onsubmit={handleSubmit} class="flex flex-col gap-4">
				{#if isRegistering}
					<Field bind:value={registerUsername} label={$LL.username()} required />
					<Field bind:value={registerEmail} label={$LL.email()} required />
					<Field bind:value={registerFirstName} label={$LL.firstName()} />
					<Field bind:value={registerLastName} label={$LL.lastName()} />
					<Field bind:value={registerPassword} label={$LL.password()} hidden required />
					<Field
						bind:value={registerConfirmPassword}
						label={$LL.confirmPassword()}
						hidden
						required
					/>
				{:else}
					<Field bind:value={loginUsername} label={$LL.usernameOrEmail()} required />
					<Field bind:value={loginPassword} label={$LL.password()} hidden required />
				{/if}

				<button
					type="submit"
					class="w-full rounded bg-primary px-4 py-3 font-semibold text-white disabled:cursor-not-allowed disabled:bg-gray-400 dark:disabled:bg-gray-600"
					disabled={isLoading}
				>
					{#if isLoading}
						<Loading class="m-auto" />
					{:else}
						{isRegistering ? $LL.register() : $LL.login()}
					{/if}
				</button>
			</form>

			<div class="mt-4 text-center">
				<button
					type="button"
					class="text-primary underline transition-colors hover:text-secondary disabled:cursor-not-allowed disabled:text-gray-400"
					onclick={toggleMode}
					disabled={isLoading}
				>
					{isRegistering ? $LL.alreadyHaveAccount() : $LL.needAccount()}
				</button>
			</div>
		</div>
	</div>
</div>
