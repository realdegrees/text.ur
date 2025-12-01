<script lang="ts">
	import SaveIcon from '~icons/material-symbols/save-outline';
	import CancelIcon from '~icons/material-symbols/close-rounded';
	import PermissionSelector from '$lib/components/permissionSelector.svelte';
	import DateTimePicker from '$lib/components/DateTimePicker.svelte';
	import type { Permission } from '$api/types';

	let {
		permissions = $bindable<Permission[]>([]),
		label = $bindable<string>(''),
		expiresAt = $bindable<string | null>(null),
		allowAnonymous = $bindable<boolean>(false),
		onCreate,
		onCancel
	}: {
		permissions?: Permission[];
		label?: string;
		expiresAt?: string | null;
		allowAnonymous?: boolean;
		onCreate: () => void;
		onCancel: () => void;
	} = $props();

	function addPermission(permission: Permission) {
		if (!permissions.includes(permission)) {
			permissions = [...permissions, permission];
		}
	}

	function removePermission(permission: Permission) {
		permissions = permissions.filter((p) => p !== permission);
	}
</script>

<div class="flex flex-col gap-3 rounded border border-text/20 bg-background/50 p-4">
	<div class="flex items-center justify-between">
		<h3 class="font-semibold">New Share Link</h3>
		<button type="button" onclick={onCancel} class="text-text/50 transition hover:text-text">
			<CancelIcon class="h-5 w-5" />
		</button>
	</div>

	<input
		type="text"
		bind:value={label}
		maxlength="30"
		placeholder="Label (optional)"
		class="rounded border border-text/20 bg-background px-3 py-2 text-sm transition-colors focus:border-text/50 focus:outline-none"
	/>

	<div class="flex flex-col gap-1">
		<div class="text-xs font-semibold text-text/70">Permissions</div>
		<PermissionSelector
			bind:selectedPermissions={permissions}
			onAdd={addPermission}
			onRemove={removePermission}
		/>
	</div>

	<DateTimePicker bind:value={expiresAt} id="create-expires" />

	<label class="flex items-center gap-2 text-sm">
		<input type="checkbox" bind:checked={allowAnonymous} class="h-4 w-4 rounded" />
		<span class="text-text/70">Allow anonymous access</span>
	</label>

	<button
		type="button"
		onclick={onCreate}
		class="flex items-center justify-center gap-2 rounded bg-primary px-4 py-2 text-text transition hover:bg-primary/80"
	>
		<SaveIcon class="h-5 w-5" />
		<span>Create</span>
	</button>
</div>
