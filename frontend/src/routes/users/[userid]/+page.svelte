<script lang="ts">
	import { api } from '$api/client';
	import { invalidateAll } from '$app/navigation';
	import { notification } from '$lib/stores/notificationStore';
	import { LL } from '$i18n/i18n-svelte';
	import Field from '$lib/components/advancedInput.svelte';
	import Loading from '~icons/svg-spinners/90-ring-with-bg';
	import type { UserUpdate, UserPrivate } from '$api/types';

	let { data } = $props();

	console.log(data);

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
</script>

<div class="flex h-full w-full flex-col items-center justify-start">
	<div class="flex h-full w-[30%] flex-col items-start justify-start gap-6 p-6">
		<div class="w-full rounded-lg bg-inset p-6 shadow-inner shadow-black/50">
			<h1 class="text-3xl font-bold text-text">{$LL.userSettings.title()}</h1>
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
	</div>
</div>
