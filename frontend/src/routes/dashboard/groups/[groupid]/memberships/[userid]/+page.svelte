<script lang="ts">
	import type { PageData } from './$types';
	import type { ScoreRead, DocumentRead, ScoreConfigRead } from '$api/types';
	import { api } from '$api/client';
	import { notification } from '$lib/stores/notificationStore';
	import BackIcon from '~icons/material-symbols/arrow-back';
	import PersonIcon from '~icons/material-symbols/person-outline';
	import CrownIcon from '~icons/material-symbols/crown-outline';
	import AdminIcon from '~icons/material-symbols/shield-outline';
	import InfoIcon from '~icons/material-symbols/info-outline';
	import { formatDateTime } from '$lib/util/dateFormat';
	import { page } from '$app/stores';
	import LL from '$i18n/i18n-svelte';

	let { data }: { data: PageData } = $props();

	let member = $derived(data.member);
	let documents: DocumentRead[] = $derived(data.documents);
	let user = $derived(member.user);

	let isOwner = $derived(member.is_owner);
	let isAdmin = $derived(member.permissions.includes('administrator'));

	let selectedDocumentId = $state<string | null>(null);
	let score = $state<ScoreRead>(data.score);
	let scoreConfig = $derived(data.scoreConfig as ScoreConfigRead | null);
	let loading = $state(false);
	let legendOpen = $state(false);

	const BASE_CATEGORIES = $derived([
		{
			label: $LL.memberScore.highlights(),
			icon: '\u{1F4DD}',
			count: 'highlights' as const,
			points: 'highlight_points' as const
		},
		{
			label: $LL.permissionGroups.comments(),
			icon: '\u{1F4AC}',
			count: 'comments' as const,
			points: 'comment_points' as const
		},
		{
			label: $LL.tags.title(),
			icon: '\u{1F3F7}\u{FE0F}',
			count: 'tags' as const,
			points: 'tag_points' as const
		}
	]);

	let legendReactions = $derived(scoreConfig?.reactions ?? []);

	let reactionBreakdown = $derived(score.breakdown.reaction_breakdown ?? []);

	let timeAgo = $derived.by(() => {
		const now = new Date();
		const cached = new Date(score.cached_at);
		const diffMs = now.getTime() - cached.getTime();
		const diffMin = Math.floor(diffMs / 60000);
		if (diffMin < 1) return $LL.memberScore.justNow();
		if (diffMin === 1) return $LL.memberScore.oneMinAgo();
		if (diffMin < 60) return $LL.memberScore.nMinAgo({ count: diffMin });
		return formatDateTime(score.cached_at);
	});

	async function fetchScore(documentId: string | null) {
		loading = true;
		try {
			const url = documentId
				? `/groups/${$page.params.groupid}/memberships/${$page.params.userid}/score?document_id=${documentId}`
				: `/groups/${$page.params.groupid}/memberships/${$page.params.userid}/score`;

			const result = await api.get<ScoreRead>(url);
			if (result.success) {
				score = result.data;
			} else {
				notification(result.error);
			}
		} finally {
			loading = false;
		}
	}

	function handleDocumentChange(event: Event) {
		const target = event.target as HTMLSelectElement;
		selectedDocumentId = target.value || null;
		fetchScore(selectedDocumentId);
	}
</script>

<div class="flex h-full w-full flex-col gap-4 p-6">
	<!-- Back link -->
	<a
		href="/dashboard/groups/{$page.params.groupid}/memberships"
		class="flex w-fit items-center gap-1.5 text-sm text-text/50 transition-colors hover:text-text/70"
	>
		<BackIcon class="h-4 w-4" />
		{$LL.memberScore.backToMembers()}
	</a>

	<!-- User Header -->
	<div class="flex items-center gap-4">
		<div class="flex h-14 w-14 items-center justify-center rounded-full bg-primary/15 text-primary">
			<PersonIcon class="h-7 w-7" />
		</div>
		<div>
			<div class="flex items-center gap-2">
				<h1 class="text-2xl font-bold">{user.username}</h1>
				{#if isOwner}
					<span
						class="flex items-center gap-1 rounded-full bg-amber-500/15 px-2 py-0.5 text-xs font-medium text-amber-600"
					>
						<CrownIcon class="h-3.5 w-3.5" />
						{$LL.memberScore.owner()}
					</span>
				{:else if isAdmin}
					<span
						class="flex items-center gap-1 rounded-full bg-blue-500/15 px-2 py-0.5 text-xs font-medium text-blue-600"
					>
						<AdminIcon class="h-3.5 w-3.5" />
						{$LL.memberScore.admin()}
					</span>
				{/if}
			</div>
			{#if user.first_name || user.last_name}
				<p class="text-sm text-text/50">
					{[user.first_name, user.last_name].filter(Boolean).join(' ')}
				</p>
			{/if}
		</div>
	</div>

	<hr class="border-text/10" />

	<!-- Score Section -->
	<div class="flex flex-col gap-4">
		<!-- Score Header Row -->
		<div class="flex flex-wrap items-center justify-between gap-2">
			<h2 class="text-xl font-semibold">{$LL.memberScore.scoreTitle()}</h2>
			<div class="flex items-center gap-3">
				<span class="text-xs text-text/40">{$LL.memberScore.updatedAgo({ time: timeAgo })}</span>
			</div>
		</div>

		<!-- Document Filter + Legend Row -->
		<div class="flex flex-wrap items-center gap-3">
			{#if documents.length > 0}
				<select
					class="rounded border border-text/15 bg-inset px-3 py-1.5 text-sm text-text transition outline-none focus:border-primary/50"
					onchange={handleDocumentChange}
					value={selectedDocumentId ?? ''}
				>
					<option value="">{$LL.memberScore.allDocuments()}</option>
					{#each documents as doc (doc.id)}
						<option value={doc.id}>{doc.name}</option>
					{/each}
				</select>
			{/if}

			<button
				class="flex cursor-pointer items-center gap-1 text-xs text-text/40 transition-colors hover:text-text/60"
				onclick={() => (legendOpen = !legendOpen)}
			>
				<InfoIcon class="h-3.5 w-3.5" />
				{legendOpen ? $LL.memberScore.hidePointSystem() : $LL.memberScore.showPointSystem()}
			</button>
		</div>

		<!-- Point System Legend (collapsible) -->
		{#if legendOpen}
			<div class="rounded-lg border border-text/10 bg-text/[0.02] p-3 text-xs text-text/60">
				<p class="mb-3 font-medium text-text/70">{$LL.memberScore.howPointsEarned()}</p>

				<div class="flex flex-col items-start gap-6 sm:flex-row">
					<!-- Action points (left) -->
					<div class="w-full sm:w-auto sm:min-w-48">
						<table class="w-full">
							<thead>
								<tr class="border-b border-text/10 text-left text-text/50">
									<th class="pb-1.5 font-medium">{$LL.groupSettings.scoring.action()}</th>
									<th class="pb-1.5 text-right font-medium"
										>{$LL.groupSettings.scoring.pointsHeader()}</th
									>
								</tr>
							</thead>
							<tbody>
								<tr class="border-b border-text/5">
									<td class="py-1.5">{$LL.groupSettings.scoring.createHighlight()}</td>
									<td class="py-1.5 text-right font-medium text-text/80"
										>{scoreConfig?.highlight_points ?? 1}</td
									>
								</tr>
								<tr class="border-b border-text/5">
									<td class="py-1.5">{$LL.groupSettings.scoring.writeComment()}</td>
									<td class="py-1.5 text-right font-medium text-text/80"
										>{scoreConfig?.comment_points ?? 5}</td
									>
								</tr>
								<tr>
									<td class="py-1.5">{$LL.groupSettings.scoring.addTag()}</td>
									<td class="py-1.5 text-right font-medium text-text/80"
										>{scoreConfig?.tag_points ?? 2}</td
									>
								</tr>
							</tbody>
						</table>
					</div>

					<!-- Reaction points (right) -->
					{#if legendReactions.length > 0}
						<div class="w-full sm:flex-1">
							<table class="w-full">
								<thead>
									<tr class="border-b border-text/10 text-left text-text/50">
										<th class="pb-1.5 font-medium">{$LL.groupSettings.scoring.emoji()}</th>
										<th class="pb-1.5 text-right font-medium"
											>{$LL.groupSettings.scoring.received()}</th
										>
										<th class="pb-1.5 text-right font-medium"
											>{$LL.groupSettings.scoring.fromAdmin()}</th
										>
										<th class="pb-1.5 text-right font-medium"
											>{$LL.groupSettings.scoring.giver()}</th
										>
									</tr>
								</thead>
								<tbody>
									{#each legendReactions as r (r.id)}
										<tr class="border-b border-text/5">
											<td class="py-1.5 text-base">{r.emoji}</td>
											<td class="py-1.5 text-right font-medium text-text/80">{r.points}</td>
											<td class="py-1.5 text-right font-medium text-text/80">{r.admin_points}</td>
											<td class="py-1.5 text-right font-medium text-text/80">{r.giver_points}</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					{/if}
				</div>
			</div>
		{/if}

		<!-- Total Score Card -->
		<div class="rounded-lg bg-primary/10 p-4" class:opacity-50={loading}>
			<p class="text-sm font-medium text-text/60">
				{$LL.memberScore.totalScore()}{#if selectedDocumentId === null && documents.length > 0}<span
						class="ml-1 font-normal text-text/40"
					>
						{$LL.memberScore.acrossDocuments({ count: documents.length })}</span
					>{/if}
			</p>
			<p class="text-4xl font-bold text-primary">
				{score.total}<span class="ml-1.5 text-base font-medium text-primary/60">{$LL.points()}</span
				>
			</p>
		</div>

		<!-- Base Breakdown Grid (highlights, comments, tags) -->
		<div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3" class:opacity-50={loading}>
			{#each BASE_CATEGORIES as cat (cat.label)}
				{@const count = score.breakdown[cat.count]}
				{@const points = score.breakdown[cat.points]}
				<div class="rounded-lg border border-text/10 bg-text/[0.02] p-3">
					<div class="flex items-center gap-2">
						<span class="text-lg">{cat.icon}</span>
						<span class="text-sm font-medium text-text/70">{cat.label}</span>
					</div>
					<div class="mt-2 flex items-baseline justify-between">
						<span class="text-2xl font-bold">{count}</span>
						<span class="text-sm text-text/40">{points} {$LL.points()}</span>
					</div>
				</div>
			{/each}
		</div>

		<!-- Per-Reaction Breakdown -->
		{#if reactionBreakdown.length > 0}
			<h3 class="mt-2 text-sm font-semibold text-text/70">{$LL.memberScore.reactions()}</h3>
			<div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3" class:opacity-50={loading}>
				{#each reactionBreakdown as rb (rb.group_reaction_id)}
					{@const totalCount = rb.received_count + rb.given_count}
					{@const totalPoints = rb.received_points + rb.given_points}
					<div class="rounded-lg border border-text/10 bg-text/[0.02] p-3">
						<div class="flex items-center gap-2">
							<span class="text-lg">{rb.emoji}</span>
						</div>
						<div class="mt-2 flex items-baseline justify-between">
							<div class="flex flex-col">
								<span class="text-2xl font-bold">{totalCount}</span>
								<div class="flex gap-3 text-[11px] text-text/40">
									<span>{$LL.memberScore.received({ count: rb.received_count })}</span>
									<span>{$LL.memberScore.given({ count: rb.given_count })}</span>
								</div>
							</div>
							<span class="text-sm text-text/40">{totalPoints} {$LL.points()}</span>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>
