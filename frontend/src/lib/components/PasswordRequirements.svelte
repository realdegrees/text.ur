<script lang="ts">
	import LL from '$i18n/i18n-svelte';

	let { password = '' }: { password: string } = $props();

	let rules = $derived([
		{ met: password.length >= 8, label: $LL.passwordRequirements.minLength() },
		{ met: /[a-z]/.test(password), label: $LL.passwordRequirements.lowercase() },
		{ met: /[A-Z]/.test(password), label: $LL.passwordRequirements.uppercase() },
		{ met: /\d/.test(password), label: $LL.passwordRequirements.digit() },
		{ met: /[^a-zA-Z0-9]/.test(password), label: $LL.passwordRequirements.special() }
	]);
</script>

{#if password.length > 0}
	<div class="flex flex-col gap-1 text-xs">
		<p class="text-muted font-medium">{$LL.passwordRequirements.title()}</p>
		{#each rules as rule (rule.label)}
			<div class="flex items-center gap-1.5">
				<span class={rule.met ? 'text-green-500' : 'text-red-400'}>
					{rule.met ? '\u2713' : '\u2717'}
				</span>
				<span class={rule.met ? 'text-muted' : 'text-text'}>{rule.label}</span>
			</div>
		{/each}
	</div>
{/if}
