<script lang="ts">
	import type { CommentRead, Visibility } from '$api/types';
	import { documentStore } from '$lib/runes/document.svelte';
	import Dropdown from '$lib/components/dropdown.svelte';
	import LL from '$i18n/i18n-svelte';
	import LockIcon from '~icons/material-symbols/lock';
	import GroupIcon from '~icons/material-symbols/group';
	import PublicIcon from '~icons/material-symbols/public';

	interface Props {
		comment: CommentRead;
		visibility: Visibility;
		canEdit?: boolean;
		isTopLevel?: boolean;
	}

	let { comment, visibility, canEdit = false, isTopLevel = false }: Props = $props();

	let isOpen = $state(false);
	let isUpdating = $state(false);
	let currentVisibility = $derived<Visibility>(visibility);

	const visibilityOptions: Visibility[] = ['private', 'restricted', 'public'];

	const getIcon = (vis: Visibility) => {
		if (vis === 'private') return LockIcon;
		if (vis === 'restricted') return GroupIcon;
		return PublicIcon;
	};

	const iconSize = 'h-3.5 w-3.5';

	const handleSelect = async (newVisibility: Visibility) => {
		if (newVisibility === visibility || isUpdating) return;
		isUpdating = true;

		try {
			comment.visibility = newVisibility;
			await documentStore.comments.update(comment);
			currentVisibility = newVisibility;
		} finally {
			isUpdating = false;
		}
	};
</script>

<div class="visibility-selector relative">
	<button
		class="flex items-center gap-1 rounded px-1 py-0.5 text-text/40 transition-colors hover:bg-text/10 hover:text-text/60 disabled:opacity-50"
		onclick={(e) => {
			e.stopPropagation();
			isOpen = !isOpen;
		}}
		disabled={isUpdating || !canEdit}
		title={canEdit
			? $LL.comments.visibility.select()
			: $LL.comments.visibility.current({ level: currentVisibility.valueOf() })}
	>
		{#if currentVisibility === 'private'}
			<LockIcon class={iconSize} />
		{:else if currentVisibility === 'restricted'}
			<GroupIcon class={iconSize} />
		{:else}
			<PublicIcon class={iconSize} />
		{/if}
	</button>

	<Dropdown
		items={visibilityOptions}
		bind:currentItem={currentVisibility}
		bind:show={isOpen}
		position={isTopLevel ? 'bottom-left' : 'top-left'}
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
				title={$LL.comments.visibility[item].description()}
			>
				<ItemIcon class={iconSize} />
				<span class="whitespace-nowrap">{$LL.comments.visibility[item].label()}</span>
			</div>
		{/snippet}
	</Dropdown>
</div>
