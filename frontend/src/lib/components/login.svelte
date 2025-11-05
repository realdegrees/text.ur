<!-- src/lib/components/LoginButton.svelte -->
<script lang="ts">
	import { goto } from '$app/navigation';
	import LoginIcon from '~icons/material-symbols/login';
	import { LL } from '$i18n/i18n-svelte';
</script>

<button
	class="bg-discord group flex h-full w-full clickable flex-row items-center justify-between rounded p-1"
	onclick={() => goto('/login')}
>
	<LoginIcon />
	<p class="ml-1 font-semibold">{$LL.login()}</p>
</button>
