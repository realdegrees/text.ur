<script lang="ts">
	import GroupIcon from '~icons/material-symbols/group-outline';
	import AddIcon from '~icons/material-symbols/add-2-rounded';
	import SelectIcon from '~icons/material-symbols/touch-app-outline';
	import ArrowLeftIcon from '~icons/material-symbols/arrow-back';
	import LL from '$i18n/i18n-svelte';

	let { data } = $props();

	const hasGroups = $derived(data.memberships && data.memberships.data.length > 0);
	const hasInvites = $derived(data.invites && data.invites.data.length > 0);
</script>

<div class="flex h-full w-full flex-col items-center justify-center p-6">
	{#if hasGroups}
		<!-- User has groups - prompt to select one -->
		<div
			class="flex max-w-md flex-col items-center gap-6 rounded-lg border border-text/10 bg-inset p-8 text-center shadow-lg"
		>
			<div class="rounded-full bg-primary/10 p-4">
				<SelectIcon class="h-12 w-12 text-primary" />
			</div>

			<div class="flex flex-col gap-2">
				<h2 class="text-2xl font-bold">{$LL.dashboard.selectGroup()}</h2>
				<p class="text-text/70">
					{$LL.dashboard.selectGroupDescription()}
				</p>
			</div>

			<div class="flex items-center gap-2 text-sm text-text/50">
				<ArrowLeftIcon class="h-5 w-5" />
				<span>{$LL.dashboard.selectFromSidebar()}</span>
			</div>
		</div>
	{:else}
		<!-- User has no groups - show getting started guide -->
		<div
			class="flex max-w-lg flex-col items-center gap-6 rounded-lg border border-text/10 bg-inset p-8 text-center shadow-lg"
		>
			<div class="rounded-full bg-primary/10 p-4">
				<GroupIcon class="h-12 w-12 text-primary" />
			</div>

			<div class="flex flex-col gap-2">
				<h2 class="text-2xl font-bold">{$LL.dashboard.welcome()}</h2>
				<p class="text-text/70">
					{$LL.dashboard.noGroupsDescription()}
				</p>
			</div>

			<div class="flex flex-col gap-4 text-left">
				<div class="flex items-start gap-3">
					<div
						class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-bold text-background"
					>
						1
					</div>
					<p class="text-sm text-text/80">{$LL.dashboard.step1()}</p>
				</div>
				<div class="flex items-start gap-3">
					<div
						class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-bold text-background"
					>
						2
					</div>
					<p class="text-sm text-text/80">{$LL.dashboard.step2()}</p>
				</div>
				<div class="flex items-start gap-3">
					<div
						class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-bold text-background"
					>
						3
					</div>
					<p class="text-sm text-text/80">{$LL.dashboard.step3()}</p>
				</div>
			</div>

			<a
				href="/dashboard/groups/create"
				class="mt-2 flex items-center gap-2 rounded-lg bg-primary px-6 py-3 font-semibold text-background transition-all hover:bg-primary/80"
			>
				<AddIcon class="h-5 w-5" />
				<span>{$LL.dashboard.createGroup()}</span>
			</a>

			{#if hasInvites}
				<p class="text-sm text-text/50">
					{$LL.dashboard.orAcceptInvite()}
				</p>
			{/if}
		</div>
	{/if}
</div>
