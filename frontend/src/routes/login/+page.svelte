<script lang="ts">
	import TabContainer from '$lib/components/TabContainer.svelte';
	import LoginForm from '$lib/components/LoginForm.svelte';
	import RegisterForm from '$lib/components/RegisterForm.svelte';
	import { invalidateAll } from '$app/navigation';

	function handleSuccess() {
		invalidateAll();
	}
</script>

<div class="flex h-fit w-full justify-center mt-20">
	<div class="w-full max-w-md overflow-hidden rounded-lg bg-inset shadow-lg">
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