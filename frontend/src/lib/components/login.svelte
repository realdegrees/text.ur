<!-- src/lib/components/LoginButton.svelte -->
<script lang="ts">
	import { goto } from '$app/navigation';
	import LoginIcon from '~icons/material-symbols/login';
	import { LL } from '$i18n/i18n-svelte';
</script>

<button
	class="rounded bg-discord flex flex-row justify-between items-center p-1 group w-full h-full clickable"
	onclick={() => goto('/login')}
>
	<LoginIcon />
	<p class="ml-1 font-semibold">{$LL.login()}</p>
</button>
