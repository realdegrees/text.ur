<script lang="ts">
	import { enhance } from '$app/forms';
	import type { ActionData } from './$types';
	import { LL } from '$i18n/i18n-svelte';
	import Loading from '~icons/svg-spinners/90-ring-with-bg';

	let {
		form = $bindable()
	}: {
		form?: ActionData;
	} = $props();

	let isRegistering = $state(false);
	let isLoading = $state(false);

	const toggleMode = () => {
		isRegistering = !isRegistering;
		form = undefined;
	};

	const handleSubmit = () => {
		isLoading = true;
		return async ({ update }: { update: () => Promise<void> }) => {
			await update();
			isLoading = false;
		};
	};
</script>

<div class="flex min-h-screen items-center justify-center p-4">
	<div class="w-full max-w-md rounded-lg bg-inset p-8 shadow-lg">
		<h1 class="mb-6 text-center text-3xl font-bold text-text">
			{isRegistering ? $LL.register() : $LL.login()}
		</h1>

		{#if form?.error}
			<div
				class="mb-4 rounded border border-red-300 bg-red-100 p-3 text-red-700 dark:border-red-700 dark:bg-red-900/30 dark:text-red-300"
				role="alert"
			>
				{form.error}
			</div>
		{/if}

		{#if form && 'success' in form && form.success}
			<div
				class="mb-4 rounded border border-green-300 bg-green-100 p-3 text-green-700 dark:border-green-700 dark:bg-green-900/30 dark:text-green-300"
				role="status"
			>
				{form.message}
			</div>
		{/if}

		<form
			method="POST"
			action="?/{isRegistering ? 'register' : 'login'}"
			use:enhance={handleSubmit}
		>
			{#if isRegistering}
				<div class="mb-4">
					<label for="username" class="mb-2 block font-medium text-text">
						{$LL.username()} <span class="text-red-600 dark:text-red-400">*</span>
					</label>
					<input
						type="text"
						id="username"
						name="username"
						required
						disabled={isLoading}
						autocomplete="username"
						class="w-full rounded border border-gray-300 bg-background px-3 py-2 text-text focus:border-transparent focus:ring-2 focus:ring-primary focus:outline-none disabled:cursor-not-allowed disabled:bg-gray-100 dark:border-gray-600 dark:disabled:bg-gray-800"
					/>
				</div>

				<div class="mb-4">
					<label for="email" class="mb-2 block font-medium text-text">
						{$LL.email()} <span class="text-red-600 dark:text-red-400">*</span>
					</label>
					<input
						type="email"
						id="email"
						name="email"
						required
						disabled={isLoading}
						autocomplete="email"
						class="w-full rounded border border-gray-300 bg-background px-3 py-2 text-text focus:border-transparent focus:ring-2 focus:ring-primary focus:outline-none disabled:cursor-not-allowed disabled:bg-gray-100 dark:border-gray-600 dark:disabled:bg-gray-800"
					/>
				</div>

				<div class="mb-4">
					<label for="firstName" class="mb-2 block font-medium text-text">
						{$LL.firstName()}
					</label>
					<input
						type="text"
						id="firstName"
						name="firstName"
						disabled={isLoading}
						autocomplete="given-name"
						class="w-full rounded border border-gray-300 bg-background px-3 py-2 text-text focus:border-transparent focus:ring-2 focus:ring-primary focus:outline-none disabled:cursor-not-allowed disabled:bg-gray-100 dark:border-gray-600 dark:disabled:bg-gray-800"
					/>
				</div>

				<div class="mb-4">
					<label for="lastName" class="mb-2 block font-medium text-text">
						{$LL.lastName()}
					</label>
					<input
						type="text"
						id="lastName"
						name="lastName"
						disabled={isLoading}
						autocomplete="family-name"
						class="w-full rounded border border-gray-300 bg-background px-3 py-2 text-text focus:border-transparent focus:ring-2 focus:ring-primary focus:outline-none disabled:cursor-not-allowed disabled:bg-gray-100 dark:border-gray-600 dark:disabled:bg-gray-800"
					/>
				</div>

				<div class="mb-4">
					<label for="password" class="mb-2 block font-medium text-text">
						{$LL.password()} <span class="text-red-600 dark:text-red-400">*</span>
					</label>
					<input
						type="password"
						id="password"
						name="password"
						required
						disabled={isLoading}
						autocomplete="new-password"
						class="w-full rounded border border-gray-300 bg-background px-3 py-2 text-text focus:border-transparent focus:ring-2 focus:ring-primary focus:outline-none disabled:cursor-not-allowed disabled:bg-gray-100 dark:border-gray-600 dark:disabled:bg-gray-800"
					/>
				</div>

				<div class="mb-6">
					<label for="confirmPassword" class="mb-2 block font-medium text-text">
						{$LL.confirmPassword()} <span class="text-red-600 dark:text-red-400">*</span>
					</label>
					<input
						type="password"
						id="confirmPassword"
						name="confirmPassword"
						required
						disabled={isLoading}
						autocomplete="new-password"
						class="w-full rounded border border-gray-300 bg-background px-3 py-2 text-text focus:border-transparent focus:ring-2 focus:ring-primary focus:outline-none disabled:cursor-not-allowed disabled:bg-gray-100 dark:border-gray-600 dark:disabled:bg-gray-800"
					/>
				</div>
			{:else}
				<div class="mb-4">
					<label for="username" class="mb-2 block font-medium text-text">
						{$LL.usernameOrEmail()} <span class="text-red-600 dark:text-red-400">*</span>
					</label>
					<input
						type="text"
						id="username"
						name="username"
						required
						disabled={isLoading}
						autocomplete="username"
						class="w-full rounded border border-gray-300 bg-background px-3 py-2 text-text focus:border-transparent focus:ring-2 focus:ring-primary focus:outline-none disabled:cursor-not-allowed disabled:bg-gray-100 dark:border-gray-600 dark:disabled:bg-gray-800"
					/>
				</div>

				<div class="mb-6">
					<label for="password" class="mb-2 block font-medium text-text">
						{$LL.password()} <span class="text-red-600 dark:text-red-400">*</span>
					</label>
					<input
						type="password"
						id="password"
						name="password"
						required
						disabled={isLoading}
						autocomplete="current-password"
						class="w-full rounded border border-gray-300 bg-background px-3 py-2 text-text focus:border-transparent focus:ring-2 focus:ring-primary focus:outline-none disabled:cursor-not-allowed disabled:bg-gray-100 dark:border-gray-600 dark:disabled:bg-gray-800"
					/>
				</div>
			{/if}

			<button
				type="submit"
				class="w-full clickable rounded bg-primary px-4 py-3 font-semibold text-white disabled:cursor-not-allowed disabled:bg-gray-400 dark:disabled:bg-gray-600"
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
