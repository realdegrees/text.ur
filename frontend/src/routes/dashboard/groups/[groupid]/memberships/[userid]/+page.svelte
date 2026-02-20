<script lang="ts">
	import type { PageData } from './$types';
	import type { ScoreRead, DocumentRead } from '$api/types';
	import { api } from '$api/client';
	import BackIcon from '~icons/material-symbols/arrow-back';
	import PersonIcon from '~icons/material-symbols/person-outline';
	import CrownIcon from '~icons/material-symbols/crown-outline';
	import AdminIcon from '~icons/material-symbols/shield-outline';
	import InfoIcon from '~icons/material-symbols/info-outline';
	import { formatDateTime } from '$lib/util/dateFormat';
	import { page } from '$app/stores';

	let { data }: { data: PageData } = $props();

	let member = $derived(data.member);
	let documents: DocumentRead[] = $derived(data.documents);
	let user = $derived(member.user);

	let isOwner = $derived(member.is_owner);
	let isAdmin = $derived(member.permissions.includes('administrator'));

	let selectedDocumentId = $state<string | null>(null);
	let score = $state<ScoreRead>(data.score);
	let loading = $state(false);
	let legendOpen = $state(false);

	const SCORE_CATEGORIES = [
		{
			label: 'Highlights',
			icon: '\u{1F4DD}',
			count: 'highlights' as const,
			points: 'highlight_points' as const
		},
		{
			label: 'Comments',
			icon: '\u{1F4AC}',
			count: 'comments' as const,
			points: 'comment_points' as const
		},
		{
			label: 'Tags',
			icon: '\u{1F3F7}\u{FE0F}',
			count: 'tags' as const,
			points: 'tag_points' as const
		},
		{
			label: 'Reactions received',
			icon: '\u{1F44D}',
			count: 'reactions_received' as const,
			points: 'reaction_received_points' as const
		},
		{
			label: 'Reactions given',
			icon: '\u{2764}\u{FE0F}',
			count: 'reactions_given' as const,
			points: 'reaction_given_points' as const
		}
	];

	const LEGEND_ITEMS = [
		{ action: 'Create a highlight', points: '1 pt' },
		{ action: 'Write a comment', points: '5 pts' },
		{ action: 'Add a tag', points: '2 pts' },
		{ action: 'Receive a reaction', points: '2 pts' },
		{ action: 'Receive a reaction from admin', points: '4 pts' },
		{ action: 'Give a reaction', points: '2 pts' }
	];

	let timeAgo = $derived.by(() => {
		const now = new Date();
		const cached = new Date(score.cached_at);
		const diffMs = now.getTime() - cached.getTime();
		const diffMin = Math.floor(diffMs / 60000);
		if (diffMin < 1) return 'just now';
		if (diffMin === 1) return '1 min ago';
		if (diffMin < 60) return `${diffMin} min ago`;
		return formatDateTime(score.cached_at);
	});

	async function fetchScore(documentId: string | null) {
		loading = true;
		const url = documentId
			? `/groups/${$page.params.groupid}/memberships/${$page.params.userid}/score?document_id=${documentId}`
			: `/groups/${$page.params.groupid}/memberships/${$page.params.userid}/score`;

		const result = await api.get<ScoreRead>(url);
		if (result.success) {
			score = result.data;
		}
		loading = false;
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
		Back to Members
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
						Owner
					</span>
				{:else if isAdmin}
					<span
						class="flex items-center gap-1 rounded-full bg-blue-500/15 px-2 py-0.5 text-xs font-medium text-blue-600"
					>
						<AdminIcon class="h-3.5 w-3.5" />
						Admin
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
			<h2 class="text-xl font-semibold">Score</h2>
			<div class="flex items-center gap-3">
				<span class="text-xs text-text/40">Updated {timeAgo}</span>
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
					<option value="">All Documents</option>
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
				{legendOpen ? 'Hide' : 'Show'} point system
			</button>
		</div>

		<!-- Point System Legend (collapsible) -->
		{#if legendOpen}
			<div class="rounded-lg border border-text/10 bg-text/[0.02] p-3 text-xs text-text/60">
				<p class="mb-2 font-medium text-text/70">How points are earned</p>
				<div class="grid grid-cols-2 gap-x-6 gap-y-1 sm:grid-cols-3">
					{#each LEGEND_ITEMS as item (item.action)}
						<div class="flex justify-between gap-2">
							<span>{item.action}</span>
							<span class="font-medium text-text/80">{item.points}</span>
						</div>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Total Score Card -->
		<div class="rounded-lg bg-primary/10 p-4" class:opacity-50={loading}>
			<p class="text-sm font-medium text-text/60">
				Total Score{#if selectedDocumentId === null && documents.length > 0}<span
						class="ml-1 font-normal text-text/40"
					>
						across {documents.length} document{documents.length === 1 ? '' : 's'}</span
					>{/if}
			</p>
			<p class="text-4xl font-bold text-primary">
				{score.total}<span class="ml-1.5 text-base font-medium text-primary/60">pts</span>
			</p>
		</div>

		<!-- Breakdown Grid -->
		<div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3" class:opacity-50={loading}>
			{#each SCORE_CATEGORIES as cat (cat.label)}
				{@const count = score.breakdown[cat.count]}
				{@const points = score.breakdown[cat.points]}
				<div class="rounded-lg border border-text/10 bg-text/[0.02] p-3">
					<div class="flex items-center gap-2">
						<span class="text-lg">{cat.icon}</span>
						<span class="text-sm font-medium text-text/70">{cat.label}</span>
					</div>
					<div class="mt-2 flex items-baseline justify-between">
						<span class="text-2xl font-bold">{count}</span>
						<span class="text-sm text-text/40">{points} pts</span>
					</div>
				</div>
			{/each}
		</div>

		<!-- Admin reactions detail -->
		{#if score.breakdown.reactions_received_from_admin > 0}
			<p class="text-xs text-text/40">
				Includes {score.breakdown.reactions_received_from_admin}
				reaction{score.breakdown.reactions_received_from_admin === 1 ? '' : 's'} from admins (4 pts each).
			</p>
		{/if}
	</div>
</div>
