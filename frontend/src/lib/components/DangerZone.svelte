<script lang="ts">
	import type { Snippet } from 'svelte';
	import DeleteIcon from '~icons/material-symbols/delete-outline';
	import Loading from '~icons/svg-spinners/90-ring-with-bg';

	interface Props {
		variant?: 'danger' | 'warning';
		title: string;
		description: string;
		actionLabel: string;
		actionIcon?: Snippet;
		onConfirm?: () => void | Promise<void>;
		loading?: boolean;
		confirmText?: string;
		confirmPrompt?: string;
		confirmTitle?: string;
		children?: Snippet;
		class?: string;
	}

	let {
		variant = 'danger',
		title,
		description,
		actionLabel,
		actionIcon,
		onConfirm,
		loading = false,
		confirmText,
		confirmPrompt,
		confirmTitle,
		children,
		class: className = ''
	}: Props = $props();

	let showConfirm = $state(false);
	let inputValue = $state('');

	let isConfirmEnabled = $derived(!confirmText || inputValue === confirmText);

	const colorStyles = $derived(
		variant === 'danger'
			? {
					container: 'border-red-500/30 bg-red-500/5',
					title: 'text-red-500',
					expandedBg: 'bg-red-500/10',
					actionBtn: 'bg-red-500/20 hover:bg-red-500/30',
					confirmBtn:
						'bg-red-500/30 hover:bg-red-500/40 disabled:cursor-not-allowed disabled:opacity-50'
				}
			: {
					container: 'border-orange-500/30 bg-orange-500/5',
					title: 'text-orange-500',
					expandedBg: 'bg-orange-500/10',
					actionBtn: 'bg-orange-500/20 hover:bg-orange-500/30',
					confirmBtn:
						'bg-orange-500/30 hover:bg-orange-500/40 disabled:cursor-not-allowed disabled:opacity-50'
				}
	);

	function handleCancel() {
		showConfirm = false;
		inputValue = '';
	}
</script>

<div class="flex flex-col gap-4 rounded-md border p-4 {colorStyles.container} {className}">
	<h2 class="text-lg font-semibold {colorStyles.title}">{title}</h2>
	<p class="text-sm text-text/70">{description}</p>

	{#if children}
		{@render children()}
	{:else if confirmText}
		{#if !showConfirm}
			<button
				type="button"
				onclick={() => (showConfirm = true)}
				class="flex w-fit flex-row items-center gap-2 rounded-md px-4 py-2 transition-colors {colorStyles.actionBtn}"
			>
				{#if actionIcon}
					{@render actionIcon()}
				{:else}
					<DeleteIcon class="h-5 w-5" />
				{/if}
				<span>{actionLabel}</span>
			</button>
		{:else}
			<div class="flex flex-col gap-3 rounded-md p-4 {colorStyles.expandedBg}">
				{#if confirmTitle}
					<p class="font-semibold {colorStyles.title}">{confirmTitle}</p>
				{/if}
				{#if confirmPrompt}
					<p class="text-sm text-text/70">{confirmPrompt}</p>
				{/if}
				<input
					type="text"
					bind:value={inputValue}
					placeholder={confirmText}
					class="form-input-danger"
				/>
				<div class="flex flex-row gap-2">
					<button
						type="button"
						onclick={() => onConfirm?.()}
						disabled={!isConfirmEnabled || loading}
						class="rounded px-4 py-2 font-semibold transition {colorStyles.confirmBtn}"
					>
						{#if loading}
							<Loading class="m-auto" />
						{:else}
							{actionLabel}
						{/if}
					</button>
					<button type="button" onclick={handleCancel} class="btn-secondary"> Cancel </button>
				</div>
			</div>
		{/if}
	{/if}
</div>
