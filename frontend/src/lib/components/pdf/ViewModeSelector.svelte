<script lang="ts">
	import { api } from '$api/client';
	import type { ViewMode1 } from '$api/types';
	import { documentStore } from '$lib/runes/document.svelte.js';
	import { sessionStore } from '$lib/runes/session.svelte.js';
	import { notification } from '$lib/stores/notificationStore';
	import LockIcon from '~icons/material-symbols/lock';
	import PublicIcon from '~icons/material-symbols/public';

	interface Props {
		isExpanded?: boolean;
	}

	let { isExpanded = false }: Props = $props();

	// Only admins and owners can change view mode
	let canChangeViewMode = $derived(
		sessionStore.routeMembership?.is_owner ||
			sessionStore.routeMembership?.permissions.includes('administrator')
	);

	let currentViewMode = $derived(documentStore.loadedDocument?.view_mode ?? 'public');
	let isUpdating = $state(false);

	const viewModes: { mode: ViewMode1; icon: typeof LockIcon; label: string; shortLabel: string }[] =
		[
			{
				mode: 'restricted',
				icon: LockIcon,
				label: 'Restricted - Owner, admins & users with permission see comments',
				shortLabel: 'Restricted'
			},
			{
				mode: 'public',
				icon: PublicIcon,
				label: 'Public - Comments visible based on their visibility settings',
				shortLabel: 'Public'
			}
		];

	const setViewMode = async (mode: ViewMode1) => {
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
		// On success, WebSocket will also broadcast this to other users
		isUpdating = false;
	};
</script>

<div class="flex {isExpanded ? 'w-full flex-col' : 'flex-col items-center'} gap-0.5">
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
				<Icon class="h-4 w-4" />
				{#if isExpanded}<span class="text-xs">{shortLabel}</span>{/if}
			</span>
		</button>
	{/each}
</div>
