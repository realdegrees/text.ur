<script lang="ts">
	import CopyIcon from '~icons/material-symbols/content-copy-outline';
	import EditIcon from '~icons/material-symbols/edit-outline';
	import DeleteIcon from '~icons/material-symbols/delete-outline';
	import RotateIcon from '~icons/material-symbols/refresh-rounded';
	import CheckIcon from '~icons/material-symbols/check';
	import ConfirmButton from '$lib/components/ConfirmButton.svelte';
	import Badge from '$lib/components/badge.svelte';
	import LL from '$i18n/i18n-svelte.js';
	import type { ShareLinkRead, Permission } from '$api/types';
	import { formatDateTime } from '$lib/util/dateFormat';

	let {
		link,
		onEdit,
		onDelete,
		onCopy,
		onRotate
	}: {
		link: ShareLinkRead;
		onEdit: () => void;
		onDelete: () => void;
		onCopy: () => void;
		onRotate: () => void;
	} = $props();
</script>

<div class="flex flex-col gap-2 rounded border border-text/20 bg-background/50 p-3">
	<div class="flex items-start justify-between gap-2">
		<div class="flex flex-col gap-1">
			<div class="flex items-center gap-2">
				{#if link.num_memberships > 0}
					<span
						class="rounded bg-blue-500/20 px-2 py-0.5 text-xs font-semibold text-blue-600"
						title="Members using this link: {link.num_memberships}"
						>{link.num_memberships} User{link.num_memberships === 1 ? '' : 's'}</span
					>
				{/if}
				{#if link.label}
					<span class="font-semibold">{link.label}</span>
				{:else}
					<span class="font-semibold text-text/50">Untitled Link</span>
				{/if}
				{#if link.allow_anonymous_access}
					<span
						class="rounded bg-green-500/20 px-2 py-0.5 text-xs font-semibold text-green-600"
						title="Allows access without an account">Anonymous</span
					>
				{/if}
			</div>
			<p class="text-xs text-text/50">
				{link.created_at !== link.updated_at ? 'last updated' : 'created'} by {link.author
					?.username || 'Deleted User'} at {formatDateTime(
					link.created_at !== link.updated_at ? link.updated_at : link.created_at
				)}
			</p>
			<p class="text-xs text-text/50">
				Expires: {formatDateTime(link.expires_at)}
			</p>
		</div>
		<div class="flex gap-1">
			<button
				type="button"
				onclick={onCopy}
				class="rounded bg-blue-500/20 p-2 transition hover:bg-blue-500/30"
				title="Copy Link"
			>
				<CopyIcon class="h-4 w-4" />
			</button>

			<button
				type="button"
				onclick={onEdit}
				class="rounded bg-text/10 p-2 transition hover:bg-text/20"
				title="Edit"
			>
				<EditIcon class="h-4 w-4" />
			</button>

			<ConfirmButton onConfirm={onRotate} slideoutDirection="left">
				{#snippet button(isOpen)}
					<div class="bg-amber-400/30 p-2 transition hover:bg-amber-400/60" title="Rotate Token">
						{#if !isOpen}
							<RotateIcon class="h-4 w-4" />
						{:else}
							<CheckIcon class="h-4 w-4" />
						{/if}
					</div>
				{/snippet}

				{#snippet slideout()}
					<p class="flex h-full w-full items-center bg-amber-400/10 px-2 text-xs text-amber-400">
						This will remove {link.num_memberships} member{link.num_memberships === 1 ? '' : 's'} from
						the group. Are you sure?
					</p>
				{/snippet}
			</ConfirmButton>

			<ConfirmButton onConfirm={onDelete} slideoutDirection="left">
				{#snippet button(isOpen)}
					<div class="bg-red-500/20 p-2 transition hover:bg-red-500/30" title="Delete">
						{#if !isOpen}
							<DeleteIcon class="h-4 w-4" />
						{:else}
							<CheckIcon class="h-4 w-4" />
						{/if}
					</div>
				{/snippet}

				{#snippet slideout()}
					<p class="flex items-center bg-red-500/10 px-2 py-0.5 text-xs text-red-500">Delete?</p>
				{/snippet}
			</ConfirmButton>
		</div>
	</div>

	<div class="flex flex-wrap gap-1">
		{#each link.permissions as perm (perm)}
			<Badge
				item={perm}
				label={$LL.permissions[perm as Permission]?.() || perm}
				showRemove={false}
			/>
		{/each}
	</div>
</div>
