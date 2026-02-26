<script lang="ts">
	import LL from '$i18n/i18n-svelte';
	import { api } from '$api/client';
	import { notification } from '$lib/stores/notificationStore';
	import { sessionStore } from '$lib/runes/session.svelte';
	import DownloadIcon from '~icons/material-symbols/download';

	let exporting = $state(false);

	async function handleExport() {
		const user = sessionStore.currentUser;
		if (!user) return;

		exporting = true;
		try {
			const result = await api.get<Record<string, unknown>>(`/users/${user.id}/export`);
			if (!result.success) {
				notification(result.error);
				return;
			}

			// Trigger a browser download of the JSON data
			const blob = new Blob([JSON.stringify(result.data, null, 2)], {
				type: 'application/json'
			});
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = 'text-ur-data-export.json';
			document.body.appendChild(a);
			a.click();
			document.body.removeChild(a);
			URL.revokeObjectURL(url);
		} finally {
			exporting = false;
		}
	}
</script>

<div class="mx-auto max-w-4xl overflow-y-auto p-8">
	<h1 class="mb-6 text-3xl font-bold">{$LL.privacy.title()}</h1>

	<!-- Responsible body -->
	<section class="mb-8">
		<h2 class="mb-3 text-xl font-semibold">{$LL.privacy.responsibleBody.title()}</h2>
		<p class="mb-2 whitespace-pre-line text-text/80">{$LL.privacy.responsibleBody.content()}</p>
	</section>

	<!-- Data Protection Officer -->
	<section class="mb-8">
		<h2 class="mb-3 text-xl font-semibold">{$LL.privacy.dpo.title()}</h2>
		<p class="mb-2 whitespace-pre-line text-text/80">{$LL.privacy.dpo.content()}</p>
	</section>

	<!-- Supervisory authority -->
	<section class="mb-8">
		<h2 class="mb-3 text-xl font-semibold">{$LL.privacy.supervisory.title()}</h2>
		<p class="mb-2 whitespace-pre-line text-text/80">{$LL.privacy.supervisory.content()}</p>
	</section>

	<!-- Purpose and legal basis -->
	<section class="mb-8">
		<h2 class="mb-3 text-xl font-semibold">{$LL.privacy.purpose.title()}</h2>
		<p class="mb-2 text-text/80">{$LL.privacy.purpose.content()}</p>
	</section>

	<!-- Data collected -->
	<section class="mb-8">
		<h2 class="mb-3 text-xl font-semibold">{$LL.privacy.dataCollected.title()}</h2>
		<p class="mb-4 text-text/80">{$LL.privacy.dataCollected.account()}</p>
		<p class="mb-4 text-text/80">{$LL.privacy.dataCollected.content()}</p>
		<p class="mb-2 text-text/80">{$LL.privacy.dataCollected.files()}</p>
	</section>

	<!-- Cookies -->
	<section class="mb-8">
		<h2 class="mb-3 text-xl font-semibold">{$LL.privacy.cookies.title()}</h2>
		<p class="mb-4 text-text/80">{$LL.privacy.cookies.description()}</p>
		<div class="overflow-x-auto">
			<table class="w-full border-collapse text-sm">
				<thead>
					<tr class="border-b border-text/20">
						<th class="p-2 text-left font-semibold">{$LL.privacy.cookies.name()}</th>
						<th class="p-2 text-left font-semibold">{$LL.privacy.cookies.purpose()}</th>
						<th class="p-2 text-left font-semibold">{$LL.privacy.cookies.expiry()}</th>
					</tr>
				</thead>
				<tbody>
					<tr class="border-b border-text/10">
						<td class="p-2 font-mono text-xs">access_token</td>
						<td class="p-2 text-text/80">{$LL.privacy.cookies.accessToken()}</td>
						<td class="p-2 text-text/80">{$LL.privacy.cookies.accessTokenExpiry()}</td>
					</tr>
					<tr class="border-b border-text/10">
						<td class="p-2 font-mono text-xs">refresh_token</td>
						<td class="p-2 text-text/80">{$LL.privacy.cookies.refreshToken()}</td>
						<td class="p-2 text-text/80">{$LL.privacy.cookies.refreshTokenExpiry()}</td>
					</tr>
					<tr class="border-b border-text/10">
						<td class="p-2 font-mono text-xs">theme</td>
						<td class="p-2 text-text/80">{$LL.privacy.cookies.theme()}</td>
						<td class="p-2 text-text/80">{$LL.privacy.cookies.themeExpiry()}</td>
					</tr>
					<tr class="border-b border-text/10">
						<td class="p-2 font-mono text-xs">locale</td>
						<td class="p-2 text-text/80">{$LL.privacy.cookies.locale()}</td>
						<td class="p-2 text-text/80">{$LL.privacy.cookies.localeExpiry()}</td>
					</tr>
				</tbody>
			</table>
		</div>
	</section>

	<!-- Server logs -->
	<section class="mb-8">
		<h2 class="mb-3 text-xl font-semibold">{$LL.privacy.logs.title()}</h2>
		<p class="mb-2 text-text/80">{$LL.privacy.logs.content()}</p>
	</section>

	<!-- Third parties -->
	<section class="mb-8">
		<h2 class="mb-3 text-xl font-semibold">{$LL.privacy.thirdParties.title()}</h2>
		<p class="mb-2 text-text/80">{$LL.privacy.thirdParties.content()}</p>
	</section>

	<!-- Your rights -->
	<section class="mb-8">
		<h2 class="mb-3 text-xl font-semibold">{$LL.privacy.rights.title()}</h2>
		<p class="mb-4 text-text/80">{$LL.privacy.rights.content()}</p>

		<!-- Data export -->
		<h3 class="mb-2 text-lg font-medium">{$LL.privacy.rights.exportTitle()}</h3>
		<p class="mb-3 text-text/80">{$LL.privacy.rights.exportDescription()}</p>
		{#if sessionStore.currentUser}
			<button
				class="flex items-center gap-2 rounded bg-primary px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
				onclick={handleExport}
				disabled={exporting}
			>
				<DownloadIcon class="h-4 w-4" />
				{exporting ? $LL.loading() : $LL.privacy.rights.exportButton()}
			</button>
		{:else}
			<p class="text-sm italic text-text/60">{$LL.privacy.rights.exportLoginRequired()}</p>
		{/if}

		<!-- Account deletion -->
		<h3 class="mb-2 mt-6 text-lg font-medium">{$LL.privacy.rights.deletionTitle()}</h3>
		<p class="text-text/80">{$LL.privacy.rights.deletionDescription()}</p>
	</section>

	<!-- Contact -->
	<section class="mb-8">
		<h2 class="mb-3 text-xl font-semibold">{$LL.privacy.contact.title()}</h2>
		<p class="text-text/80">{$LL.privacy.contact.content()}</p>
	</section>
</div>
