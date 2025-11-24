<script lang="ts">
	import type { Visibility } from '$api/types';
	import { documentStore } from '$lib/runes/document.svelte.js';
	import LockIcon from '~icons/material-symbols/lock';
	import GroupIcon from '~icons/material-symbols/group';
	import PublicIcon from '~icons/material-symbols/public';

	interface Props {
		commentId: number;
		visibility: Visibility;
		size?: 'sm' | 'md';
	}

	let { commentId, visibility, size = 'md' }: Props = $props();

	let isOpen = $state(false);
	let isUpdating = $state(false);

	const visibilityLabels: Record<Visibility, string> = {
		private: 'Private - Only you',
		restricted: 'Restricted - Authorized users',
		public: 'Public - Everyone'
	};

	const iconSize = $derived(size === 'sm' ? 'h-3 w-3' : 'h-3.5 w-3.5');

	const handleSelect = async (newVisibility: Visibility) => {
		if (newVisibility === visibility || isUpdating) return;
		isUpdating = true;
		isOpen = false;

		try {
			await documentStore.updateComment(commentId, { visibility: newVisibility });
		} finally {
			isUpdating = false;
		}
	};

	const handleClickOutside = (e: MouseEvent) => {
		const target = e.target as HTMLElement;
		if (!target.closest('.visibility-selector')) {
			isOpen = false;
		}
	};

	$effect(() => {
		if (isOpen) {
			document.addEventListener('click', handleClickOutside);
			return () => document.removeEventListener('click', handleClickOutside);
		}
	});
</script>

<div class="visibility-selector relative">
	<button
		class="flex items-center gap-1 rounded px-1 py-0.5 text-text/40 transition-colors hover:bg-text/10 hover:text-text/60 disabled:opacity-50"
		onclick={(e) => {
			e.stopPropagation();
			isOpen = !isOpen;
		}}
		disabled={isUpdating}
		title={visibilityLabels[visibility]}
	>
		{#if visibility === 'private'}
			<LockIcon class={iconSize} />
		{:else if visibility === 'restricted'}
			<GroupIcon class={iconSize} />
		{:else}
			<PublicIcon class={iconSize} />
		{/if}
	</button>

	{#if isOpen}
		<div
			class="absolute top-full left-0 z-50 mt-1 min-w-36 rounded-lg border border-text/10 bg-background py-1 shadow-lg"
		>
			<button
				class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs transition-colors hover:bg-text/5 {visibility ===
				'private'
					? 'text-primary'
					: 'text-text/70'}"
				onclick={(e) => {
					e.stopPropagation();
					handleSelect('private');
				}}
			>
				<LockIcon class="h-3.5 w-3.5" />
				<span>Private - Only you</span>
			</button>
			<button
				class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs transition-colors hover:bg-text/5 {visibility ===
				'restricted'
					? 'text-primary'
					: 'text-text/70'}"
				onclick={(e) => {
					e.stopPropagation();
					handleSelect('restricted');
				}}
			>
				<GroupIcon class="h-3.5 w-3.5" />
				<span>Restricted - Authorized users</span>
			</button>
			<button
				class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs transition-colors hover:bg-text/5 {visibility ===
				'public'
					? 'text-primary'
					: 'text-text/70'}"
				onclick={(e) => {
					e.stopPropagation();
					handleSelect('public');
				}}
			>
				<PublicIcon class="h-3.5 w-3.5" />
				<span>Public - Everyone</span>
			</button>
		</div>
	{/if}
</div>
