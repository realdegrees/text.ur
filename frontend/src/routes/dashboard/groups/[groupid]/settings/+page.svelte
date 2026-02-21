<script lang="ts">
	import SaveIcon from '~icons/material-symbols/save-outline';
	import DeleteIcon from '~icons/material-symbols/delete-outline';
	import TransferIcon from '~icons/material-symbols/swap-horiz';
	import AddIcon from '~icons/material-symbols/add';
	import LL from '$i18n/i18n-svelte';
	import { api } from '$api/client';
	import { notification } from '$lib/stores/notificationStore';
	import { sessionStore } from '$lib/runes/session.svelte.js';
	import { goto, invalidateAll } from '$app/navigation';
	import type {
		GroupUpdate,
		GroupTransfer,
		Permission,
		UserRead,
		MembershipRead,
		ScoreConfigRead,
		ScoreConfigUpdate,
		GroupReactionRead,
		GroupReactionCreate,
		GroupReactionUpdate,
		Emoji
	} from '$api/types';
	import type { Paginated } from '$api/pagination';
	import AdvancedInput from '$lib/components/advancedInput.svelte';
	import PermissionSelector from '$lib/components/permissionSelector.svelte';
	import { emojiSchema } from '$api/schemas';

	let { data } = $props();
	let group = $derived(data.membership.group);
	let isOwner = $derived(sessionStore.routeMembership?.is_owner);
	let defaultPermissions: Permission[] = $state(data.membership.group.default_permissions || []);

	let transferUsername: string = $state('');
	let selectedTransferUser: UserRead | undefined = $state(undefined);
	let showDeleteConfirm: boolean = $state(false);
	let showTransferConfirm: boolean = $state(false);
	let deleteConfirmText: string = $state('');
	let editableGroupName: string = $state(data.membership.group.name);

	// --- Scoring config state ---
	let scoreConfig = $state<ScoreConfigRead | null>(data.scoreConfig ?? null);
	let highlightPoints = $state(data.scoreConfig?.highlight_points ?? 1);
	let commentPoints = $state(data.scoreConfig?.comment_points ?? 5);
	let tagPoints = $state(data.scoreConfig?.tag_points ?? 2);
	let reactions = $state<GroupReactionRead[]>(
		data.scoreConfig?.reactions
			? [...data.scoreConfig.reactions].sort((a, b) => a.order - b.order)
			: []
	);
	let scoreSaving = $state(false);

	// Emoji picker state
	let showEmojiPicker = $state(false);
	let addingReaction = $state(false);

	// Editing/deleting reaction state
	let editingReactionId = $state<number | null>(null);
	let confirmDeleteReactionId = $state<number | null>(null);
	let editPoints = $state(0);
	let editAdminPoints = $state(0);
	let editGiverPoints = $state(0);

	// Extract all valid emojis from the Zod schema
	const ALL_EMOJIS: Emoji[] = (emojiSchema.options as unknown as { value: Emoji }[]).map(
		(o) => o.value
	);

	// Emojis already used by this group
	let usedEmojis = $derived(new Set(reactions.map((r) => r.emoji)));
	let availableEmojis = $derived(ALL_EMOJIS.filter((e) => !usedEmojis.has(e)));

	let hasScoreChanges = $derived.by(() => {
		if (!scoreConfig) return false;
		return (
			highlightPoints !== scoreConfig.highlight_points ||
			commentPoints !== scoreConfig.comment_points ||
			tagPoints !== scoreConfig.tag_points
		);
	});

	let transferDisplayName = $derived.by(() => {
		if (!selectedTransferUser) return '';
		const u = selectedTransferUser;
		if (u.first_name || u.last_name) {
			return `${u.username} (${u.first_name || ''} ${u.last_name || ''})`;
		}
		return u.username;
	});

	let hasChanges = $derived.by(() => {
		return (
			editableGroupName !== group.name ||
			JSON.stringify(defaultPermissions) !== JSON.stringify(group.default_permissions)
		);
	});

	async function handleSave(): Promise<void> {
		const updateData: GroupUpdate = {
			name: editableGroupName !== group.name ? editableGroupName : undefined,
			default_permissions: defaultPermissions.length > 0 ? defaultPermissions : undefined
		};

		const result = await api.update(`/groups/${group.id}`, updateData);

		if (result.success) {
			notification('success', $LL.groupSettings.settingsUpdated());
			await invalidateAll();
		} else {
			notification(result.error);
		}
	}

	async function handleSaveScoreConfig(): Promise<void> {
		scoreSaving = true;
		try {
			const updateData: ScoreConfigUpdate = {
				highlight_points: highlightPoints,
				comment_points: commentPoints,
				tag_points: tagPoints
			};

			const result = await api.patch<ScoreConfigRead>(
				`/groups/${group.id}/score-config`,
				updateData
			);

			if (result.success) {
				scoreConfig = result.data;
				notification('success', $LL.groupSettings.scoring.updated());
			} else {
				notification(result.error);
			}
		} finally {
			scoreSaving = false;
		}
	}

	async function handleAddReaction(emoji: Emoji): Promise<void> {
		addingReaction = true;
		const createData: GroupReactionCreate = { emoji };

		const result = await api.post<GroupReactionRead>(`/groups/${group.id}/reactions`, createData);

		if (result.success && result.data) {
			reactions = [...reactions, result.data].sort((a, b) => a.order - b.order);
			showEmojiPicker = false;
			notification('success', $LL.groupSettings.scoring.reactionAdded({ emoji }));
		} else if (!result.success) {
			notification(result.error);
		}
		addingReaction = false;
	}

	async function handleDeleteReaction(reactionId: number): Promise<void> {
		const result = await api.delete(`/groups/${group.id}/reactions/${reactionId}`);

		if (result.success) {
			reactions = reactions.filter((r) => r.id !== reactionId);
			notification('success', $LL.groupSettings.scoring.reactionRemoved());
		} else {
			notification(result.error);
		}
	}

	function startEditReaction(reaction: GroupReactionRead): void {
		editingReactionId = reaction.id;
		editPoints = reaction.points;
		editAdminPoints = reaction.admin_points;
		editGiverPoints = reaction.giver_points;
	}

	async function handleSaveReaction(): Promise<void> {
		if (editingReactionId === null) return;
		const updateData: GroupReactionUpdate = {
			points: editPoints,
			admin_points: editAdminPoints,
			giver_points: editGiverPoints
		};

		const result = await api.patch<GroupReactionRead>(
			`/groups/${group.id}/reactions/${editingReactionId}`,
			updateData
		);

		if (result.success) {
			reactions = reactions.map((r) => (r.id === editingReactionId ? result.data : r));
			editingReactionId = null;
			notification('success', $LL.groupSettings.scoring.reactionUpdated());
		} else {
			notification(result.error);
		}
	}

	async function handleDelete(): Promise<void> {
		if (deleteConfirmText !== group.name) {
			notification('error', $LL.groupSettings.danger.nameDoesNotMatch());
			return;
		}

		const result = await api.delete(`/groups/${group.id}`);

		if (result.success) {
			notification('success', $LL.groupSettings.danger.deleteSuccess());
			await invalidateAll();
			goto('/dashboard');
		} else {
			notification(result.error);
		}
	}

	async function handleTransfer(): Promise<void> {
		if (!selectedTransferUser) {
			notification('error', $LL.groupSettings.transfer.selectUser());
			return;
		}

		const transferData: GroupTransfer = {
			user_id: selectedTransferUser.id
		};

		const result = await api.post(`/groups/${group.id}/transfer`, transferData);

		if (result.success) {
			notification('success', $LL.groupSettings.transfer.success());
			showTransferConfirm = false;
			transferUsername = '';
			selectedTransferUser = undefined;
			await invalidateAll();
		} else {
			notification(result.error);
		}
	}

	async function fetchMemberOptions(search: string): Promise<UserRead[]> {
		const response = await api.get<Paginated<MembershipRead>, 'group'>(`/memberships`, {
			filters: [
				{ field: 'group_id', operator: '==', value: group.id },
				{ field: 'accepted', operator: '==', value: 'true' },
				{ field: 'user_id', operator: '!=', value: data.sessionUser.id.toString() }
			]
		});

		if (response.success) {
			const users = response.data.data.map((m) => m.user);
			return users.filter(
				(u) =>
					u.username.toLowerCase().includes(search.toLowerCase()) ||
					u.first_name?.toLowerCase().includes(search.toLowerCase()) ||
					u.last_name?.toLowerCase().includes(search.toLowerCase())
			);
		}
		return [];
	}

	function addDefaultPermission(permission: Permission): void {
		if (!defaultPermissions.includes(permission)) {
			defaultPermissions = [...defaultPermissions, permission];
		}
	}

	function removeDefaultPermission(permission: Permission): void {
		defaultPermissions = defaultPermissions.filter((p) => p !== permission);
	}
</script>

<div class="flex h-full w-full flex-col gap-6 p-6">
	<!-- Settings Form -->
	<div class="flex flex-col gap-6">
		<!-- Group Name -->
		<div class="flex flex-col gap-2">
			<label for="groupName" class="text-sm font-semibold text-text/70">{$LL.groupSettings.groupName()}</label>
			<input
				id="groupName"
				type="text"
				bind:value={editableGroupName}
				class="rounded-md border border-text/20 bg-text/5 px-4 py-2 transition-colors focus:border-text/50 focus:outline-none"
			/>
		</div>

		<!-- Group ID (Read-only) -->
		<div class="flex flex-col gap-2">
			<label for="groupId" class="text-sm font-semibold text-text/70">{$LL.groupSettings.groupId()}</label>
			<input
				id="groupId"
				type="text"
				value={group?.id}
				readonly
				class="cursor-not-allowed rounded-md border border-text/20 bg-text/10 px-4 py-2 font-mono text-sm text-text/70"
			/>
		</div>

		<!-- Default Permissions -->
		{#if sessionStore.validatePermissions(['administrator'])}
			<div class="flex flex-col gap-2">
			<div class="text-sm font-semibold text-text/70">{$LL.groupSettings.defaultPermissions()}</div>
			<p class="text-xs text-text/50">
				{$LL.groupSettings.defaultPermissionsDescription()}
			</p>
				<PermissionSelector
					bind:selectedPermissions={defaultPermissions}
					onAdd={addDefaultPermission}
					onRemove={removeDefaultPermission}
				/>
			</div>
		{/if}

		<!-- Save Button -->
		<div class="flex flex-row justify-end gap-2">
			<button
				type="button"
				onclick={handleSave}
				class="flex flex-row items-center gap-2 rounded-md bg-primary px-6 py-2 text-text transition-all hover:bg-primary/80 disabled:cursor-not-allowed disabled:opacity-50"
				disabled={!hasChanges}
			>
				<SaveIcon class="h-5 w-5" />
				<span>{$LL.saveChanges()}</span>
			</button>
		</div>

		<!-- Scoring Configuration -->
		{#if sessionStore.validatePermissions(['administrator'])}
			<div class="mt-4 flex flex-col gap-4 rounded-md border border-text/20 bg-text/5 p-4">
			<h2 class="text-lg font-semibold text-text/90">{$LL.groupSettings.scoring.title()}</h2>
			<p class="text-xs text-text/50">
				{$LL.groupSettings.scoring.description()}
			</p>

				<!-- Side-by-side tables -->
				<div class="flex flex-col items-start gap-6 lg:flex-row">
					<!-- Action Points Table (left) -->
					<div class="flex w-full flex-col gap-3 lg:w-auto lg:min-w-64">
						<h3 class="text-sm font-semibold text-text/80">{$LL.groupSettings.scoring.actionPoints()}</h3>
						<table class="w-full text-sm">
							<thead>
								<tr class="border-b border-text/10 text-left text-xs text-text/50">
								<th class="pb-2 font-medium">{$LL.groupSettings.scoring.action()}</th>
								<th class="pb-2 text-right font-medium">{$LL.groupSettings.scoring.pointsHeader()}</th>
							</tr>
							</thead>
							<tbody>
								<tr class="border-b border-text/5">
									<td class="py-2 text-text/80">{$LL.groupSettings.scoring.createHighlight()}</td>
									<td class="py-2 text-right">
										<input
											type="number"
											min="0"
											bind:value={highlightPoints}
											class="w-20 rounded border border-text/20 bg-text/5 px-2 py-1 text-right text-sm transition-colors focus:border-text/50 focus:outline-none"
										/>
									</td>
								</tr>
								<tr class="border-b border-text/5">
									<td class="py-2 text-text/80">{$LL.groupSettings.scoring.writeComment()}</td>
									<td class="py-2 text-right">
										<input
											type="number"
											min="0"
											bind:value={commentPoints}
											class="w-20 rounded border border-text/20 bg-text/5 px-2 py-1 text-right text-sm transition-colors focus:border-text/50 focus:outline-none"
										/>
									</td>
								</tr>
								<tr>
									<td class="py-2 text-text/80">{$LL.groupSettings.scoring.addTag()}</td>
									<td class="py-2 text-right">
										<input
											type="number"
											min="0"
											bind:value={tagPoints}
											class="w-20 rounded border border-text/20 bg-text/5 px-2 py-1 text-right text-sm transition-colors focus:border-text/50 focus:outline-none"
										/>
									</td>
								</tr>
							</tbody>
						</table>

						<div class="flex flex-row justify-end">
							<button
								type="button"
								onclick={handleSaveScoreConfig}
								class="flex flex-row items-center gap-2 rounded-md bg-primary px-4 py-1.5 text-sm text-text transition-all hover:bg-primary/80 disabled:cursor-not-allowed disabled:opacity-50"
								disabled={!hasScoreChanges || scoreSaving}
							>
								<SaveIcon class="h-4 w-4" />
								<span>{scoreSaving ? $LL.groupSettings.scoring.savingPoints() : $LL.groupSettings.scoring.savePoints()}</span>
							</button>
						</div>
					</div>

					<!-- Emoji Reactions Table (right) -->
					<div class="flex w-full flex-col gap-3 lg:flex-1">
						<h3 class="text-sm font-semibold text-text/80">{$LL.groupSettings.scoring.emojiReactions()}</h3>

						{#if reactions.length > 0}
							<table class="w-full text-sm">
								<thead>
								<tr class="border-b border-text/10 text-left text-xs text-text/50">
									<th class="pb-2 font-medium">{$LL.groupSettings.scoring.emoji()}</th>
									<th class="pb-2 text-right font-medium">{$LL.groupSettings.scoring.received()}</th>
									<th class="pb-2 text-right font-medium">{$LL.groupSettings.scoring.fromAdmin()}</th>
									<th class="pb-2 text-right font-medium">{$LL.groupSettings.scoring.giver()}</th>
									<th class="pb-2 text-right font-medium"></th>
								</tr>
								</thead>
								<tbody>
									{#each reactions as reaction (reaction.id)}
										{#if editingReactionId === reaction.id}
											<tr class="border-b border-primary/20 bg-primary/5">
												<td class="py-2 text-center text-xl">{reaction.emoji}</td>
												<td class="py-2 text-right">
													<input
														type="number"
														bind:value={editPoints}
														class="w-16 rounded border border-text/20 bg-text/5 px-1.5 py-1 text-right text-xs focus:border-text/50 focus:outline-none"
													/>
												</td>
												<td class="py-2 text-right">
													<input
														type="number"
														bind:value={editAdminPoints}
														class="w-16 rounded border border-text/20 bg-text/5 px-1.5 py-1 text-right text-xs focus:border-text/50 focus:outline-none"
													/>
												</td>
												<td class="py-2 text-right">
													<input
														type="number"
														bind:value={editGiverPoints}
														class="w-16 rounded border border-text/20 bg-text/5 px-1.5 py-1 text-right text-xs focus:border-text/50 focus:outline-none"
													/>
												</td>
												<td class="py-2 text-right">
													<div class="flex justify-end gap-1">
													<button
														type="button"
														onclick={handleSaveReaction}
														class="rounded bg-primary/30 px-2 py-1 text-xs transition hover:bg-primary/50"
													>
														{$LL.save()}
													</button>
													<button
														type="button"
														onclick={() => (editingReactionId = null)}
														class="rounded bg-text/10 px-2 py-1 text-xs transition hover:bg-text/20"
													>
														{$LL.cancel()}
													</button>
													</div>
												</td>
											</tr>
										{:else}
											<tr class="border-b border-text/5">
												<td class="py-2 text-center text-xl">{reaction.emoji}</td>
												<td class="py-2 text-right text-text/70">{reaction.points}</td>
												<td class="py-2 text-right text-text/70">{reaction.admin_points}</td>
												<td class="py-2 text-right text-text/70">{reaction.giver_points}</td>
												<td class="py-2 text-right">
													{#if confirmDeleteReactionId === reaction.id}
														<div class="flex items-center justify-end gap-1">
														<span class="text-xs text-red-400/80"
															>{$LL.groupSettings.scoring.deleteExistingWarning()}</span
														>
														<button
															type="button"
															onclick={() => {
																handleDeleteReaction(reaction.id);
																confirmDeleteReactionId = null;
															}}
															class="rounded bg-red-500/20 px-2 py-1 text-xs text-red-400 transition hover:bg-red-500/30"
														>
															{$LL.confirm()}
														</button>
														<button
															type="button"
															onclick={() => (confirmDeleteReactionId = null)}
															class="rounded bg-text/10 px-2 py-1 text-xs transition hover:bg-text/20"
														>
															{$LL.cancel()}
														</button>
														</div>
													{:else}
														<div class="flex justify-end gap-1">
													<button
														type="button"
														onclick={() => startEditReaction(reaction)}
														class="rounded px-2 py-1 text-xs text-text/50 transition hover:bg-text/10 hover:text-text/80"
													>
														{$LL.edit()}
													</button>
													<button
														type="button"
														onclick={() => (confirmDeleteReactionId = reaction.id)}
														class="rounded px-2 py-1 text-xs text-red-400/70 transition hover:bg-red-500/10 hover:text-red-400"
													>
														{$LL.remove()}
													</button>
														</div>
													{/if}
												</td>
											</tr>
										{/if}
									{/each}
								</tbody>
							</table>
						{/if}

						<!-- Add reaction button / picker -->
						{#if !showEmojiPicker}
							<button
								type="button"
								onclick={() => (showEmojiPicker = true)}
								class="flex w-fit items-center gap-1.5 rounded-md border border-dashed border-text/20 px-3 py-1.5 text-sm text-text/50 transition hover:border-text/40 hover:text-text/70"
								disabled={availableEmojis.length === 0}
							>
							<AddIcon class="h-4 w-4" />
							<span>{$LL.groupSettings.scoring.addReaction()}</span>
							</button>
						{:else}
							<div class="flex flex-col gap-3 rounded-md border border-text/20 bg-text/[0.02] p-3">
							<div class="text-xs font-semibold text-text/70">
								{$LL.groupSettings.scoring.selectEmoji({ count: availableEmojis.length })}
							</div>
								<div class="flex flex-wrap gap-1">
									{#each availableEmojis as emoji (emoji)}
										<button
											type="button"
											class="cursor-pointer rounded-md p-1.5 text-lg transition-colors hover:bg-text/10"
											onclick={() => handleAddReaction(emoji)}
											disabled={addingReaction}
										>
											{emoji}
										</button>
									{/each}
								</div>
							<button
								type="button"
								onclick={() => (showEmojiPicker = false)}
								class="w-fit rounded bg-text/10 px-3 py-1 text-xs transition hover:bg-text/20"
							>
								{$LL.cancel()}
							</button>
							</div>
						{/if}
					</div>
				</div>

			<p class="text-xs text-text/40">
				{$LL.groupSettings.scoring.removeNote()}
			</p>
			</div>
		{/if}

		<!-- Transfer Ownership (Owner only) -->
		{#if isOwner}
			<div
				class="mt-8 flex flex-col gap-4 rounded-md border border-orange-500/30 bg-orange-500/5 p-4"
			>
			<h2 class="text-lg font-semibold text-orange-500">{$LL.groupSettings.transfer.title()}</h2>
			<p class="text-sm text-text/70">
				{$LL.groupSettings.transfer.description()}
			</p>

				{#if !showTransferConfirm}
					<div class="flex flex-row items-end gap-2">
						<div class="w-64">
							<AdvancedInput
								fetchOptions={fetchMemberOptions}
								bind:value={transferUsername}
								bind:selected={selectedTransferUser}
								config={{ placeholder: $LL.groupSettings.transfer.searchPlaceholder() }}
								stringify={{
									option: (user) => `${user.username}`,
									hint: (s) => ` (${s?.first_name || ''} ${s?.last_name || ''})`
								}}
								onSubmit={() => {
									if (selectedTransferUser) {
										showTransferConfirm = true;
									}
								}}
							/>
						</div>
						<button
							type="button"
							class="rounded bg-orange-500/30 px-3 py-2.5 font-semibold shadow-inner shadow-black/30 transition hover:cursor-pointer hover:bg-orange-500/40"
							onclick={() => {
								if (selectedTransferUser) {
									showTransferConfirm = true;
								}
							}}
							disabled={!selectedTransferUser}
							class:opacity-50={!selectedTransferUser}
							class:cursor-not-allowed={!selectedTransferUser}
						>
						<TransferIcon class="inline h-5 w-5" />
						{$LL.groupSettings.transfer.button()}
					</button>
					</div>
				{:else}
					<div class="flex flex-col gap-3 rounded-md bg-orange-500/10 p-4">
						<p class="font-semibold text-orange-500">{$LL.groupSettings.transfer.confirmTitle()}</p>
						<p class="text-sm text-text/70">
							{$LL.groupSettings.transfer.confirmMessage({ username: transferDisplayName })}
						</p>
						<div class="flex flex-row gap-2">
							<button
								type="button"
								onclick={handleTransfer}
								class="rounded bg-orange-500/30 px-4 py-2 font-semibold transition hover:bg-orange-500/40"
							>
								{$LL.groupSettings.transfer.confirmButton()}
							</button>
							<button
								type="button"
								onclick={() => {
									showTransferConfirm = false;
									transferUsername = '';
									selectedTransferUser = undefined;
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

		<!-- Danger Zone (Owner only) -->
		{#if isOwner}
			<div class="mt-8 flex flex-col gap-4 rounded-md border border-red-500/30 bg-red-500/5 p-4">
			<h2 class="text-lg font-semibold text-red-500">{$LL.groupSettings.danger.title()}</h2>
			<p class="text-sm text-text/70">
				{$LL.groupSettings.danger.description()}
			</p>

				{#if !showDeleteConfirm}
					<button
						type="button"
						onclick={() => (showDeleteConfirm = true)}
						class="flex w-fit flex-row items-center gap-2 rounded-md bg-red-500/20 px-4 py-2 transition-all hover:bg-red-500/30"
					>
					<DeleteIcon class="h-5 w-5" />
					<span>{$LL.groupSettings.danger.deleteButton()}</span>
					</button>
				{:else}
					<div class="flex flex-col gap-3 rounded-md bg-red-500/10 p-4">
						<p class="font-semibold text-red-500">{$LL.groupSettings.danger.confirmTitle()}</p>
						<p class="text-sm text-text/70">
							{$LL.groupSettings.danger.confirmMessage({ name: group.name })}
						</p>
						<input
							type="text"
							bind:value={deleteConfirmText}
							placeholder={group.name}
							class="rounded-md border border-red-500/30 bg-text/5 px-4 py-2 transition-colors focus:border-red-500/50 focus:outline-none"
						/>
						<div class="flex flex-row gap-2">
							<button
								type="button"
								onclick={handleDelete}
								disabled={deleteConfirmText !== group.name}
								class="rounded bg-red-500/30 px-4 py-2 font-semibold transition hover:bg-red-500/40 disabled:cursor-not-allowed disabled:opacity-50"
							>
								{$LL.groupSettings.danger.deleteButton()}
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
