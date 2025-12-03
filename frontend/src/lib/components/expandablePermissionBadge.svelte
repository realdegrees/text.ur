<script lang="ts">
	import type { Permission } from '$api/types';
	import Badge from '$lib/components/badge.svelte';
	import LL from '$i18n/i18n-svelte.js';

	let {
		permissions,
		label,
		variant = 'default'
	} = $props<{
		permissions: Permission[];
		label: string;
		variant?: 'default' | 'sharelink';
	}>();

	const badgeColors = {
		default: '#3b82f6',
		sharelink: '#a855f7'
	};
</script>

{#if permissions.length > 0}
	<div class="group/expand-perm flex flex-row flex-wrap gap-1.5">
		<!-- Compact badge - hidden on hover -->
		<div class="group-hover/expand-perm:hidden">
			<Badge
				item={label}
				{label}
				showRemove={false}
				disabled={true}
				customColor={variant === 'sharelink' ? badgeColors.sharelink : badgeColors.default}
			/>
		</div>

		<!-- Expanded badges - shown on hover -->
		<div class="hidden flex-row flex-wrap gap-1.5 group-hover/expand-perm:flex">
			{#each permissions as perm (perm)}
				<Badge
					item={perm}
					label={($LL.permissions as Record<string, () => string>)[perm]?.() || perm}
					showRemove={false}
					disabled={true}
					customColor={variant === 'sharelink' ? badgeColors.sharelink : badgeColors.default}
				/>
			{/each}
		</div>
	</div>
{/if}
