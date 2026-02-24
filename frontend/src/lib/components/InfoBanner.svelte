<script lang="ts">
	import type { Snippet } from 'svelte';
	import InfoIcon from '~icons/material-symbols/info-outline';
	import WarningIcon from '~icons/material-symbols/warning-outline';
	import ErrorIcon from '~icons/material-symbols/error-outline';

	interface Props {
		variant: 'info' | 'warning' | 'danger' | 'error';
		title?: string;
		icon?: boolean;
		children: Snippet;
		class?: string;
	}

	let { variant, title, icon = true, children, class: className = '' }: Props = $props();

	const variantStyles = $derived(
		{
			info: {
				container: 'border-primary/30 bg-primary/5',
				title: 'text-primary',
				icon: 'text-primary'
			},
			warning: {
				container: 'border-amber-500/30 bg-amber-500/10',
				title: 'text-amber-600 dark:text-amber-400',
				icon: 'text-amber-600 dark:text-amber-400'
			},
			danger: {
				container: 'border-red-500/30 bg-red-500/10',
				title: 'text-red-600 dark:text-red-400',
				icon: 'text-red-600 dark:text-red-400'
			},
			error: {
				container: 'border-red-500/30 bg-red-500/10',
				title: 'text-red-600 dark:text-red-400',
				icon: 'text-red-600 dark:text-red-400'
			}
		}[variant]
	);

	const IconComponent = $derived(
		variant === 'info' ? InfoIcon : variant === 'warning' ? WarningIcon : ErrorIcon
	);
</script>

<div class="flex gap-2.5 rounded-md border p-3 text-sm {variantStyles.container} {className}">
	{#if icon}
		<IconComponent class="mt-0.5 h-4 w-4 shrink-0 {variantStyles.icon}" />
	{/if}
	<div class="flex-1">
		{#if title}
			<p class="mb-1 font-semibold {variantStyles.title}">{title}</p>
		{/if}
		{@render children()}
	</div>
</div>
