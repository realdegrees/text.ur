<script lang="ts">
	import AddIcon from '~icons/material-symbols/add-2-rounded';
	import type { Permission } from '$api/types';
	import Badge from '$lib/components/badge.svelte';
	import Dropdown from '$lib/components/dropdown.svelte';
	import { permissionSchema } from '$api/schemas';
	import LL from '$i18n/i18n-svelte.js';

	let {
		selectedPermissions = $bindable([]),
		onAdd,
		onRemove,
		disabled = false,
		showRemove = true,
		allowSelection = true,
	} = $props<{
		selectedPermissions: Permission[];
		onAdd: (permission: Permission) => void;
		onRemove: (permission: Permission) => void;
		disabled?: boolean;
		showRemove?: boolean;
		allowSelection?: boolean;
	}>();

	const availablePermissions = permissionSchema.options.map((p) => p.value);

	const availableToAdd = $derived(
		availablePermissions.filter((p) => !selectedPermissions.includes(p))
	);

</script>

<div class="flex flex-wrap items-center gap-1.5">
	{#each selectedPermissions as perm (perm)}
		<Badge
			item={perm}
			label={$LL.permissions[perm as Permission]?.() || perm}
			{showRemove}
			onRemove={() => onRemove(perm)}
			{disabled}
		/>
	{/each}

	{#if availableToAdd.length > 0}
		<Dropdown
			items={availableToAdd}
			onSelect={(perm) => onAdd(perm)}
			position="bottom-left"
			title="Add Permission"
			showArrow={false}
			show={false}
			hideCurrentSelection={true}
			{allowSelection}
		>
			{#snippet icon()}
				<AddIcon
					class={`h-5.5 w-5.5 rounded bg-background text-text shadow-inner shadow-black/20 transition-all hover:bg-green-500/30 ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
				/>
			{/snippet}
			{#snippet itemSnippet(perm)}
				<p class="p-1 text-left text-text">{$LL.permissions[perm]?.() || perm}</p>
			{/snippet}
		</Dropdown>
	{/if}
</div>
