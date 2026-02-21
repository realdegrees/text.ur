<script lang="ts">
	import { api } from '$api/client';
	import type { ViewMode } from '$api/types';
	import { documentStore } from '$lib/runes/document.svelte.js';
	import { sessionStore } from '$lib/runes/session.svelte.js';
	import { notification } from '$lib/stores/notificationStore';
	import LL from '$i18n/i18n-svelte';
	import LockIcon from '~icons/material-symbols/lock';
	import PublicIcon from '~icons/material-symbols/public';
	import QuestionMarkIcon from '~icons/material-symbols/help-outline';

	interface Props {
		isExpanded?: boolean;
		iconSizeClass?: string;
	}

	let { isExpanded = false, iconSizeClass = 'h-5 w-5' }: Props = $props();

	// Only admins and owners can change view mode
	let canChangeViewMode = $derived(
		sessionStore.routeMembership?.is_owner ||
			sessionStore.routeMembership?.permissions.includes('administrator')
	);

	let currentViewMode = $derived(documentStore.loadedDocument?.view_mode ?? 'public');
	let isUpdating = $state(false);

	const viewModes = $derived([
		{
			mode: 'restricted' as ViewMode,
			icon: LockIcon,
			label: $LL.pdf.viewMode.restrictedDescription(),
			shortLabel: $LL.pdf.viewMode.restricted()
		},
		{
			mode: 'public' as ViewMode,
			icon: PublicIcon,
			label: $LL.pdf.viewMode.publicDescription(),
			shortLabel: $LL.pdf.viewMode.public()
		}
	]);

	const setViewMode = async (mode: ViewMode) => {
		if (!canChangeViewMode || isUpdating || mode === currentViewMode) return;
		if (!documentStore.loadedDocument) return;

		const previousMode = documentStore.loadedDocument.view_mode;
		isUpdating = true;

		// Optimistically update local state
		documentStore.loadedDocument.view_mode = mode;

		const result = await api.update(`/documents/${documentStore.loadedDocument.id}`, {
			view_mode: mode
		});

		if (!result.success) {
			// Revert on failure
			documentStore.loadedDocument.view_mode = previousMode;
			notification(result.error);
		}
		isUpdating = false;
	};
</script>

<div class="flex {isExpanded ? 'w-full flex-col' : 'flex-col items-center'} gap-0.5">
	{#if isExpanded}
		<span class="flex flex-row items-center justify-between px-1 text-[10px] text-text/40">
			{$LL.pdf.viewMode.label()}
			{#if canChangeViewMode}
				<div title={$LL.pdf.viewMode.tooltip()}>
					<QuestionMarkIcon
						class="ml-1 h-3.5 w-3.5 text-text/40 transition-colors hover:text-text"
					/>
				</div>
			{/if}
		</span>
	{/if}
	{#each viewModes as { mode, icon: Icon, label, shortLabel } (mode)}
		<!-- Render view mode buttons; only apply hover styles when the user can change view mode -->
		<button
			class="rounded p-1.5 transition-colors {currentViewMode === mode
				? 'bg-primary/20 text-primary'
				: canChangeViewMode
					? 'text-text/50 hover:bg-text/10 hover:text-text/70'
					: 'text-text/50'} disabled:opacity-50 {isExpanded ? 'w-full' : ''}"
			onclick={() => setViewMode(mode)}
			disabled={isUpdating || !canChangeViewMode}
			aria-disabled={isUpdating || !canChangeViewMode}
			title={label}
		>
			<span class="flex items-center gap-2">
				<Icon class={iconSizeClass} />
				{#if isExpanded}<span class="text-xs">{shortLabel}</span>{/if}
			</span>
		</button>
	{/each}
</div>
