<script lang="ts">
	import type { GroupCreate, GroupRead, Permission } from '$api/types';
	import AddIcon from '~icons/material-symbols/add-2-rounded';
	import GroupIcon from '~icons/material-symbols/group-outline';
	import Loading from '~icons/svg-spinners/90-ring-with-bg';
	import { api } from '$api/client';
	import { notification } from '$lib/stores/notificationStore';
	import PermissionSelector from '$lib/components/permissionSelector.svelte';
	import { goto, invalidateAll } from '$app/navigation';
	import LL from '$i18n/i18n-svelte';

	let groupName: string = $state('');
	let selectedPermissions: Permission[] = $state(['add_comments', 'add_reactions']);
	let isLoading: boolean = $state(false);
	let errorMessage: string = $state('');

	// Default scoring values (read-only preview, matches backend DEFAULT_REACTIONS)
	let DEFAULT_ACTION_POINTS = $derived([
		{ action: $LL.groupSettings.scoring.createHighlight(), points: 1 },
		{ action: $LL.groupSettings.scoring.writeComment(), points: 5 },
		{ action: $LL.groupSettings.scoring.addTag(), points: 2 }
	]);

	const DEFAULT_EMOJI_REACTIONS = [
		{ emoji: '\u{1F44D}', points: 2, admin_points: 4, giver_points: 2 },
		{ emoji: '\u{1F60A}', points: 2, admin_points: 4, giver_points: 2 },
		{ emoji: '\u{2764}\u{FE0F}', points: 2, admin_points: 4, giver_points: 2 },
		{ emoji: '\u{1F525}', points: 2, admin_points: 4, giver_points: 2 },
		{ emoji: '\u{1FAF0}', points: 2, admin_points: 4, giver_points: 2 },
		{ emoji: '\u{1F913}', points: 2, admin_points: 4, giver_points: 2 }
	];

	function addPermission(permission: Permission): void {
		if (!selectedPermissions.includes(permission)) {
			selectedPermissions = [...selectedPermissions, permission];
		}
	}

	function removePermission(permission: Permission): void {
		selectedPermissions = selectedPermissions.filter((p) => p !== permission);
	}

	async function handleSubmit(event: Event): Promise<void> {
		event.preventDefault();

		if (!groupName.trim()) {
			errorMessage = $LL.groupCreate.groupNameRequired();
			return;
		}

		errorMessage = '';
		isLoading = true;

		const result = await api.post<GroupRead>('/groups', {
			name: groupName.trim(),
			default_permissions: selectedPermissions
		} satisfies GroupCreate);

		if (!result.success) {
			notification(result.error);
			isLoading = false;
			return;
		}

		if (!result.data) {
			notification('error', $LL.groupCreate.createFailed());
			isLoading = false;
			return;
		}

		isLoading = false;

		await invalidateAll();
		goto(`/dashboard/groups/${result.data.id}/documents`);
	}
</script>

<div class="flex h-full w-full flex-col gap-4 p-6">
	<!-- Header Section -->
	<div class="flex flex-row items-center gap-3">
		<a href="/dashboard" class="text-text/70 transition-colors hover:text-text">{$LL.dashboard.title()}</a>
		<span class="text-text/50">/</span>
		<h1 class="text-2xl font-bold">{$LL.groupCreate.title()}</h1>
	</div>

	<hr class="border-text/20" />

	<!-- Form Section -->
	<form onsubmit={handleSubmit} class="flex flex-col gap-6">
		<!-- Error Message -->
		{#if errorMessage}
			<div
				class="rounded-md border border-red-300 bg-red-100 p-3 text-red-700 dark:border-red-700 dark:bg-red-900/30 dark:text-red-300"
			>
				{errorMessage}
			</div>
		{/if}

		<!-- Group Name -->
		<div class="flex flex-col gap-2">
			<div class="flex flex-row items-center gap-2">
				<GroupIcon class="h-6 w-6" />
				<h2 class="text-xl font-semibold">{$LL.groupCreate.groupDetails()}</h2>
			</div>

			<label for="groupName" class="text-sm font-semibold text-text/70">{$LL.groupCreate.groupNameLabel()}</label>
			<input
				id="groupName"
				type="text"
				bind:value={groupName}
				required
				placeholder={$LL.groupCreate.groupNamePlaceholder()}
				class="rounded-md border border-text/20 bg-text/5 px-4 py-2 transition-colors focus:border-text/50 focus:outline-none"
				disabled={isLoading}
			/>
		</div>

		<hr class="border-text/20" />

		<!-- Default Permissions -->
		<div class="flex flex-col gap-3">
		<h2 class="text-xl font-semibold">{$LL.groupCreate.defaultPermissions.title()}</h2>
		<p class="text-sm text-text/70">
			{$LL.groupCreate.defaultPermissions.description()}
		</p>

			<PermissionSelector
				bind:selectedPermissions
				onAdd={addPermission}
				onRemove={removePermission}
				disabled={isLoading}
			/>
		</div>

		<hr class="border-text/20" />

		<!-- Scoring Configuration (read-only preview) -->
		<div class="flex flex-col gap-3">
		<h2 class="text-xl font-semibold">{$LL.groupCreate.scoring.title()}</h2>
		<p class="text-sm text-text/70">
			{$LL.groupCreate.scoring.description()}
		</p>

			<!-- Side-by-side tables -->
			<div class="flex flex-col items-start gap-6 text-sm lg:flex-row">
				<!-- Action Points (left) -->
				<div class="w-full lg:w-auto lg:min-w-56">
					<table class="w-full">
						<thead>
							<tr class="border-b border-text/10 text-left text-xs text-text/50">
							<th class="pb-2 font-medium">{$LL.groupSettings.scoring.action()}</th>
							<th class="pb-2 text-right font-medium">{$LL.groupSettings.scoring.pointsHeader()}</th>
							</tr>
						</thead>
						<tbody>
							{#each DEFAULT_ACTION_POINTS as row, i (row.action)}
								<tr class={i < DEFAULT_ACTION_POINTS.length - 1 ? 'border-b border-text/5' : ''}>
									<td class="py-2 text-text/70">{row.action}</td>
									<td class="py-2 text-right text-text/70">{row.points}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>

				<!-- Emoji Reactions (right) -->
				<div class="w-full lg:flex-1">
					<table class="w-full">
						<thead>
							<tr class="border-b border-text/10 text-left text-xs text-text/50">
							<th class="pb-2 font-medium">{$LL.groupSettings.scoring.emoji()}</th>
							<th class="pb-2 text-right font-medium">{$LL.groupSettings.scoring.received()}</th>
							<th class="pb-2 text-right font-medium">{$LL.groupSettings.scoring.fromAdmin()}</th>
							<th class="pb-2 text-right font-medium">{$LL.groupSettings.scoring.giver()}</th>
							</tr>
						</thead>
						<tbody>
							{#each DEFAULT_EMOJI_REACTIONS as r, i (r.emoji)}
								<tr class={i < DEFAULT_EMOJI_REACTIONS.length - 1 ? 'border-b border-text/5' : ''}>
									<td class="py-2 text-base">{r.emoji}</td>
									<td class="py-2 text-right text-text/70">{r.points}</td>
									<td class="py-2 text-right text-text/70">{r.admin_points}</td>
									<td class="py-2 text-right text-text/70">{r.giver_points}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			</div>
		</div>

		<hr class="border-text/20" />

		<!-- Submit Button -->
		<div class="flex flex-row justify-end gap-2">
			<a href="/dashboard" class="rounded-md bg-text/10 px-6 py-2 transition-all hover:bg-text/20">
			{$LL.cancel()}
		</a>
			<button
				type="submit"
				disabled={isLoading || !groupName.trim()}
				class="flex flex-row items-center gap-2 rounded-md bg-primary px-6 py-2 text-text transition-all hover:bg-primary/80 disabled:cursor-not-allowed disabled:bg-text/30"
			>
				{#if isLoading}
					<Loading class="h-5 w-5" />
					<span>{$LL.creating()}</span>
				{:else}
					<AddIcon class="h-5 w-5" />
					<span>{$LL.groupCreate.createButton()}</span>
				{/if}
			</button>
		</div>
	</form>
</div>
