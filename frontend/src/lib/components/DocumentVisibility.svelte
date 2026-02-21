<script lang="ts">
	import Dropdown from '$lib/components/dropdown.svelte';
	import type { DocumentRead, DocumentVisibility } from '$api/types';
	import { api } from '$api/client';
	import { notification } from '$lib/stores/notificationStore';
	import { invalidateAll } from '$app/navigation';
	import LL from '$i18n/i18n-svelte';
	import LockIcon from '~icons/material-symbols/lock';
	import PublicIcon from '~icons/material-symbols/public';
	import ChevronDown from '~icons/material-symbols/keyboard-arrow-down';

	interface Props {
		document: DocumentRead;
		canEdit?: boolean;
	}

	let { document, canEdit = false }: Props = $props();

	let isUpdating = $state(false);
	let isOpen = $state(false);
	let currentVisibility = $derived(document.visibility);

	const visibilityOptions: DocumentVisibility[] = ['private', 'public'];

	const visibilityLabels: Record<DocumentVisibility, string> = {
		private: 'Only Administrators can see this document',
		public: 'All members that can view the group can see this document'
	};

	const visibilityShortLabels: Record<DocumentVisibility, string> = {
		private: 'Private - Only Administrators',
		public: 'Public - Everyone'
	};

	const getIcon = (vis: DocumentVisibility) => {
		if (vis === 'private') return LockIcon;
		return PublicIcon;
	};

	const iconSize = 'h-4 w-4';

	async function handleSelect(newVisibility: DocumentVisibility): Promise<void> {
		if (newVisibility === document.visibility || isUpdating) return;
		isUpdating = true;

		const prev = document.visibility;

		// optimistic update
		document.visibility = newVisibility;

		const result = await api.update(`/documents/${document.id}`, {
			visibility: newVisibility
		});

		if (!result.success) {
			// revert
			document.visibility = prev;
			notification(result.error);
		} else {
			notification('success', $LL.visibility.updated());
			// refresh parent lists/state
			invalidateAll();
		}

		isUpdating = false;
		isOpen = false;
	}
</script>

<div class="visibility-selector relative">
	<button
		class="flex w-fit flex-row items-center gap-1 rounded-full px-2 py-1 text-xs font-semibold text-black/90 uppercase transition-colors {canEdit
			? 'hover:cursor-pointer'
			: ''}"
		class:bg-green-300={document.visibility === 'public'}
		class:bg-yellow-300={document.visibility === 'private'}
		onclick={(e) => {
			e.stopPropagation();
			isOpen = !isOpen;
		}}
		disabled={!canEdit || isUpdating}
		title={canEdit
			? 'Change document visibility'
			: `Document visibility: ${currentVisibility.valueOf()}`}
	>
		{#if currentVisibility === 'private'}
			<LockIcon class={iconSize} />
		{:else}
			<PublicIcon class={iconSize} />
		{/if}
		<span class="ml-2">{$LL.visibility[document.visibility].label()}</span>
		{#if canEdit}
			<ChevronDown class="ml-2 h-3.5 w-3.5" />
		{/if}
	</button>

	<Dropdown
		items={visibilityOptions}
		bind:currentItem={currentVisibility}
		bind:show={isOpen}
		position="top-left"
		allowSelection={false}
		showCurrentItemInList={true}
		onSelect={handleSelect}
	>
		{#snippet itemSnippet(item)}
			{@const ItemIcon = getIcon(item)}
			<div
				class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs transition-colors {item ===
				currentVisibility
					? 'text-primary'
					: 'text-text/70'}"
				title={visibilityLabels[item]}
			>
				<ItemIcon class={iconSize} />
				<span class="whitespace-nowrap">{visibilityShortLabels[item]}</span>
			</div>
		{/snippet}
	</Dropdown>
</div>
