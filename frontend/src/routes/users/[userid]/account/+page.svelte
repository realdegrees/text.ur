<script lang="ts">
	import { api } from '$api/client';
	import { goto, invalidateAll } from '$app/navigation';
	import { notification } from '$lib/stores/notificationStore';
	import { LL } from '$i18n/i18n-svelte';
	import Field from '$lib/components/advancedInput.svelte';
	import ConfirmButton from '$lib/components/ConfirmButton.svelte';
	import Loading from '~icons/svg-spinners/90-ring-with-bg';
	import LogoutIcon from '~icons/mdi/exit-run';
	import DeleteIcon from '~icons/material-symbols/delete-outline';
	import type { UserUpdate, UserPrivate } from '$api/types';

	let { data } = $props();

	// User info state - use $state for editable fields, initialized from props
	let username = $derived(data.sessionUser.username);
	let firstName = $derived(data.sessionUser.first_name ?? '');
	let lastName = $derived(data.sessionUser.last_name ?? '');

	// Password change state
	let oldPassword = $state('');
	let newPassword = $state('');
	let confirmPassword = $state('');

	// Guest account upgrade state
	let upgradeEmail = $state('');
	let upgradePassword = $state('');
	let upgradeConfirmPassword = $state('');
	let showUpgradeForm = $state(false);

	// Loading states
	let isUpdating = $state(false);
	let isUpgrading = $state(false);

	// Delete account state
	let showDeleteConfirm = $state(false);
	let deleteConfirmText = $state('');
	let isDeleting = $state(false);

	async function handleDeleteAccount(): Promise<void> {
		if (deleteConfirmText !== data.sessionUser.username) {
			notification('error', $LL.userSettings.danger.nameDoesNotMatch());
			return;
		}

		isDeleting = true;

		try {
			const result = await api.delete(`/users/${data.sessionUser.id}`);

			if (result.success) {
				notification('success', $LL.userSettings.danger.deleteSuccess());
				await goto('/login');
			} else {
				notification(result.error);
			}
		} finally {
			isDeleting = false;
		}
	}

	async function handleUpdateProfile() {
		isUpdating = true;

		try {
			const updateData: UserUpdate = {
				username: username !== data.sessionUser.username ? username : undefined,
				first_name: firstName !== (data.sessionUser.first_name || '') ? firstName : undefined,
				last_name: lastName !== (data.sessionUser.last_name || '') ? lastName : undefined
			};

			// Add password change if provided
			if (newPassword) {
				if (newPassword !== confirmPassword) {
					notification('error', $LL.userSettings.changePassword.errors.mismatch());
					return;
				}
				updateData.old_password = oldPassword;
				updateData.new_password = newPassword;
			}

			const result = await api.update(`/users/${data.sessionUser.id}`, updateData);

			if (!result.success) {
				notification(result.error);
				return;
			}

			notification('success', $LL.userSettings.profile.success());

			// Clear password fields
			oldPassword = '';
			newPassword = '';
			confirmPassword = '';

			// Refresh data
			await invalidateAll();
		} finally {
			isUpdating = false;
		}
	}

	async function handleUpgradeAccount() {
		if (!upgradeEmail || !upgradePassword) {
			notification('error', $LL.userSettings.upgradeAccount.errors.required());
			return;
		}

		if (upgradePassword !== upgradeConfirmPassword) {
			notification('error', $LL.userSettings.upgradeAccount.errors.passwordMismatch());
			return;
		}

		isUpgrading = true;

		try {
			// Use the register endpoint as an authenticated guest user with email+password
			// The backend will detect this and upgrade the account
			const result = await api.post('/register', {
				username: data.sessionUser.username,
				email: upgradeEmail,
				password: upgradePassword,
				first_name: data.sessionUser.first_name,
				last_name: data.sessionUser.last_name
			});

			if (!result.success) {
				notification(result.error);
				return;
			}

			notification('success', $LL.userSettings.upgradeAccount.success());
			showUpgradeForm = false;

			// Refresh data
			await invalidateAll();
		} finally {
			isUpgrading = false;
		}
	}

	async function handleLogoutAllDevices() {
		const result = await api.post('/logout/all', {});

		if (!result.success) {
			notification(result.error);
			return;
		}

		notification('success', $LL.userSettings.logoutSuccess());

		// Redirect to login page after logout
		invalidateAll();
		await goto('/login');
	}
</script>

<div class="flex h-full w-full flex-col items-center justify-start overflow-y-auto">
	<div class="flex h-full w-[30%] flex-col items-start justify-start gap-6 p-6">
		<div class="w-full rounded-lg bg-inset p-6 shadow-inner shadow-black/50">
			<div class="flex items-center justify-between">
				<h1 class="text-3xl font-bold text-text">{$LL.userSettings.title()}</h1>

				<ConfirmButton onConfirm={handleLogoutAllDevices}>
					{#snippet button(isOpen)}
						<div
							class="flex items-center gap-2 rounded border-2 px-3 py-2 text-sm font-medium transition-colors {isOpen
								? 'border-red-600/80 bg-red-600/20 text-red-700 dark:text-red-300'
								: 'border-red-500/50 bg-red-500/10 text-red-600 hover:bg-red-500/20 dark:text-red-400'}"
						>
							<LogoutIcon class="h-4 w-4" />
							{#if !isOpen}
								<p class="whitespace-nowrap">
									{data.sessionUser.is_guest
										? $LL.userSettings.logoutGuestSession()
										: $LL.userSettings.logoutAllDevices()}
								</p>
							{/if}
						</div>
					{/snippet}

					{#snippet slideout()}
						<div class="bg-red-500/10 px-3 py-2 whitespace-nowrap text-red-600 dark:text-red-400">
							{data.sessionUser.is_guest
								? $LL.userSettings.deleteGuestWarning()
								: $LL.userSettings.logoutConfirm()}
						</div>
					{/snippet}
				</ConfirmButton>
			</div>
		</div>

		{#if data.sessionUser.is_guest}
			<div
				class="w-full rounded-lg border-2 border-yellow-400 bg-yellow-50 p-4 dark:border-yellow-600 dark:bg-yellow-900/20"
			>
				<div class="flex items-start gap-3">
					<div class="text-2xl">⚠️</div>
					<div class="flex-1">
						<h3 class="font-semibold text-yellow-800 dark:text-yellow-200">
							{$LL.userSettings.guestWarning.title()}
						</h3>
						<p class="mt-1 text-sm text-yellow-700 dark:text-yellow-300">
							{$LL.userSettings.guestWarning.description()}
						</p>
						<button
							type="button"
							onclick={() => (showUpgradeForm = !showUpgradeForm)}
							class="mt-2 text-sm font-medium text-yellow-800 underline hover:text-yellow-900 dark:text-yellow-200 dark:hover:text-yellow-100"
						>
							{showUpgradeForm
								? $LL.userSettings.guestWarning.cancelButton()
								: $LL.userSettings.guestWarning.upgradeButton()}
						</button>
					</div>
				</div>
			</div>
		{/if}

		{#if data.sessionUser.is_guest && showUpgradeForm}
			<div class="w-full rounded-lg bg-inset p-6 shadow-inner shadow-black/50">
				<h2 class="mb-4 text-xl font-semibold text-text">
					{$LL.userSettings.upgradeAccount.title()}
				</h2>
				<p class="text-muted mb-4 text-sm">
					{$LL.userSettings.upgradeAccount.description()}
				</p>

				<form
					onsubmit={(e) => {
						e.preventDefault();
						handleUpgradeAccount();
					}}
					class="flex flex-col gap-4"
				>
					<Field
						name="upgradeEmail"
						label={$LL.userSettings.upgradeAccount.emailLabel()}
						bind:value={upgradeEmail}
						required
					/>
					<Field
						name="upgradePassword"
						label={$LL.userSettings.upgradeAccount.passwordLabel()}
						bind:value={upgradePassword}
						hidden
						required
					/>
					<Field
						name="upgradeConfirmPassword"
						label={$LL.userSettings.upgradeAccount.confirmPasswordLabel()}
						bind:value={upgradeConfirmPassword}
						hidden
						required
					/>

					<button
						type="submit"
						disabled={isUpgrading}
						class="w-full rounded bg-primary px-4 py-3 font-semibold text-white disabled:cursor-not-allowed disabled:bg-gray-400 dark:disabled:bg-gray-600"
					>
						{#if isUpgrading}
							<Loading class="m-auto" />
						{:else}
							{$LL.userSettings.upgradeAccount.submitButton()}
						{/if}
					</button>
				</form>
			</div>
		{/if}

		<form
			onsubmit={(e) => {
				e.preventDefault();
				handleUpdateProfile();
			}}
			class="flex w-full flex-col gap-6"
		>
			<!-- Profile Information Card -->
			<div class="w-full rounded-lg bg-inset p-6 shadow-inner shadow-black/50">
				<h2 class="mb-4 text-xl font-semibold text-text">
					{$LL.userSettings.profile.title()}
				</h2>

				<div class="flex flex-col gap-4">
					<Field
						name="username"
						label={$LL.userSettings.profile.usernameLabel()}
						bind:value={username}
						required
					/>
					<Field
						name="firstName"
						label={$LL.userSettings.profile.firstNameLabel()}
						bind:value={firstName}
					/>
					<Field
						name="lastName"
						label={$LL.userSettings.profile.lastNameLabel()}
						bind:value={lastName}
					/>
				</div>
			</div>

			<!-- Email Card (for non-guest users) -->
			{#if !data.sessionUser.is_guest && data.sessionUser.email}
				<div class="w-full rounded-lg bg-inset p-6 shadow-inner shadow-black/50">
					<h2 class="mb-4 text-xl font-semibold text-text">
						{$LL.userSettings.profile.emailLabel()}
					</h2>
					<p class="text-muted text-sm">{(data.sessionUser as UserPrivate).email}</p>
				</div>
			{/if}

			<!-- Password Change Card -->
			{#if !data.sessionUser.is_guest}
				<div class="w-full rounded-lg bg-inset p-6 shadow-inner shadow-black/50">
					<h2 class="mb-4 text-xl font-semibold text-text">
						{$LL.userSettings.changePassword.title()}
					</h2>

					<div class="flex flex-col gap-4">
						{#if !data.sessionUser.is_guest}
							<Field
								name="oldPassword"
								label={$LL.userSettings.changePassword.currentPasswordLabel()}
								bind:value={oldPassword}
								hidden
							/>
						{/if}
						<Field
							name="newPassword"
							label={$LL.userSettings.changePassword.newPasswordLabel()}
							bind:value={newPassword}
							hidden
						/>
						<Field
							name="confirmPassword"
							label={$LL.userSettings.changePassword.confirmPasswordLabel()}
							bind:value={confirmPassword}
							hidden
						/>
					</div>
				</div>
			{/if}

			<!-- Save Button (outside cards) -->
			<button
				type="submit"
				disabled={isUpdating}
				class="w-full rounded bg-primary px-4 py-3 font-semibold text-white disabled:cursor-not-allowed disabled:bg-gray-400 dark:disabled:bg-gray-600"
			>
				{#if isUpdating}
					<Loading class="m-auto" />
				{:else}
					{$LL.userSettings.profile.saveButton()}
				{/if}
			</button>
		</form>

		<!-- Danger Zone (non-guest users only) -->
		{#if !data.sessionUser.is_guest}
			<div
				class="mt-2 flex w-full flex-col gap-4 rounded-lg border border-red-500/30 bg-red-500/5 p-6"
			>
				<h2 class="text-lg font-semibold text-red-500">
					{$LL.userSettings.danger.title()}
				</h2>
				<p class="text-sm text-text/70">
					{$LL.userSettings.danger.description()}
				</p>

				{#if !showDeleteConfirm}
					<button
						type="button"
						onclick={() => (showDeleteConfirm = true)}
						class="flex w-fit flex-row items-center gap-2 rounded-md bg-red-500/20 px-4 py-2 transition-all hover:bg-red-500/30"
					>
						<DeleteIcon class="h-5 w-5" />
						<span>{$LL.userSettings.danger.deleteButton()}</span>
					</button>
				{:else}
					<div class="flex flex-col gap-3 rounded-md bg-red-500/10 p-4">
						<p class="font-semibold text-red-500">
							{$LL.userSettings.danger.confirmTitle()}
						</p>
						<p class="text-sm text-text/70">
							{$LL.userSettings.danger.confirmMessage({
								name: data.sessionUser.username
							})}
						</p>
						<input
							type="text"
							bind:value={deleteConfirmText}
							placeholder={data.sessionUser.username}
							class="rounded-md border border-red-500/30 bg-text/5 px-4 py-2 transition-colors focus:border-red-500/50 focus:outline-none"
						/>
						<div class="flex flex-row gap-2">
							<button
								type="button"
								onclick={handleDeleteAccount}
								disabled={deleteConfirmText !== data.sessionUser.username || isDeleting}
								class="rounded bg-red-500/30 px-4 py-2 font-semibold transition hover:bg-red-500/40 disabled:cursor-not-allowed disabled:opacity-50"
							>
								{#if isDeleting}
									<Loading class="m-auto" />
								{:else}
									{$LL.userSettings.danger.deleteButton()}
								{/if}
							</button>
							<button
								type="button"
								onclick={() => {
									showDeleteConfirm = false;
									deleteConfirmText = '';
								}}
								class="rounded bg-text/10 px-4 py-2 font-semibold transition hover:bg-text/20"
							>
								{$LL.cancel()}
							</button>
						</div>
					</div>
				{/if}
			</div>
		{/if}
	</div>
</div>
