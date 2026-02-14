<script lang="ts">
	import type { Component } from 'svelte';
	import LL from '$i18n/i18n-svelte';
	import SettingsIcon from '~icons/material-symbols/settings-outline';
	import PeopleIcon from '~icons/material-symbols/group-outline';
	import DocumentIcon from '~icons/material-symbols/description-outline';
	import ShareIcon from '~icons/material-symbols/link';
	import type { LocalizedString } from 'typesafe-i18n';
	import { fly } from 'svelte/transition';
	import { page } from '$app/state';
	import { sessionStore } from '$lib/runes/session.svelte.js';

	let { data, children } = $props();
	let group = $derived(data.membership.group);

	type MenuItem = {
		path: string;
		i18nKey: () => LocalizedString;
		icon: Component;
		condition: boolean;
	};

	const menuItems: MenuItem[] = $derived([
		{ path: '/documents', i18nKey: $LL.group.documents, icon: DocumentIcon, condition: true },
		{ path: '/memberships', i18nKey: $LL.group.members, icon: PeopleIcon, condition: true },
		{
			path: '/sharing',
			i18nKey: () => 'Sharing' as LocalizedString,
			icon: ShareIcon,
			condition: sessionStore.validatePermissions({
				or: ['administrator']
			})
		},
		{
			path: '/settings',
			i18nKey: $LL.group.settings,
			icon: SettingsIcon,
			condition: sessionStore.validatePermissions(['administrator'])
		}
	]);

	function isActive(itemPath: string): boolean {
		const currentPath = page.url.pathname;
		const basePath = `/dashboard/groups/${group?.id}`;

		if (itemPath === '') {
			return currentPath === basePath;
		}
		return currentPath === `${basePath}${itemPath}`;
	}
</script>

{#key page.params.groupid}
	<div
		class="flex h-full w-full flex-col gap-4"
		in:fly={{ y: -60, duration: 150, delay: 200 }}
		out:fly={{ y: -60, duration: 200 }}
	>
		<!-- Navigation Tabs -->
		<nav class="flex flex-row gap-2 border-b border-text/20">
			{#each menuItems as item (item.path)}
				{#if item.condition}
					<a
						href="/dashboard/groups/{group?.id}{item.path}"
						class="flex flex-row items-center gap-2 border-b-2 px-4 py-2 transition-all {isActive(
							item.path
						)
							? 'border-primary text-primary'
							: 'border-transparent text-text/70 hover:border-text/30 hover:text-text'}"
					>
						<item.icon class="h-5 w-5" />
						<span>{item.i18nKey()}</span>
					</a>
				{/if}
			{/each}
		</nav>

		<!-- Page Content -->
		<div class="flex-1 overflow-auto">
			{@render children?.()}
		</div>
	</div>
{/key}
