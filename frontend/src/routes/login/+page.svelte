<script lang="ts">
	import TabContainer from '$lib/components/TabContainer.svelte';
	import LoginForm from '$lib/components/LoginForm.svelte';
	import RegisterForm from '$lib/components/RegisterForm.svelte';
	import { invalidateAll } from '$app/navigation';
	import { page } from '$app/stores';

	const showResetSuccess = $derived($page.url.searchParams.get('reset') === 'success');

	function handleSuccess() {
		invalidateAll();
	}
</script>

<div class="mt-20 flex h-fit w-full justify-center">
	<div class="w-full max-w-md overflow-hidden rounded-lg bg-inset shadow-lg">
		{#if showResetSuccess}
			<div class="border-b-4 border-b-green-500 bg-green-500/20 p-2 text-text">
				Password reset successful! You can now log in with your new password.
			</div>
		{/if}
		<TabContainer
			tabs={[
				{ label: 'Login', snippet: Login },
				{ label: 'Register', snippet: Register }
			]}
		/>
	</div>
</div>

{#snippet Login()}
	<LoginForm onSuccess={handleSuccess} />
{/snippet}
{#snippet Register()}
	<RegisterForm onSuccess={handleSuccess} />
{/snippet}

<style>
	.success-banner {
		background-color: #d4edda;
		color: #155724;
		padding: 1rem;
		text-align: center;
		font-size: 0.875rem;
		border-bottom: 1px solid #c3e6cb;
	}
</style>
