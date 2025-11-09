<script lang="ts">
	import { page } from '$app/stores';
	import type { Component } from 'svelte';
	import LL from '$i18n/i18n-svelte';
	import SettingsIcon from '~icons/material-symbols/settings-outline';
	import PeopleIcon from '~icons/material-symbols/group-outline';
	import DocumentIcon from '~icons/material-symbols/description-outline';
	import type { LocalizedString } from 'typesafe-i18n';

	let { data, children } = $props();
	let group = $derived(data.selectedGroup);

	type MenuItem = {
		path: string;
		i18nKey: () => LocalizedString;
		icon: Component;
	};

	const menuItems: MenuItem[] = [
		{ path: '', i18nKey: $LL.groupDocuments, icon: DocumentIcon },
		{ path: '/memberships', i18nKey: $LL.groupMembers, icon: PeopleIcon },
		{ path: '/settings', i18nKey: $LL.groupSettings, icon: SettingsIcon }
	];

	function isActive(itemPath: string): boolean {
		const currentPath = $page.url.pathname;
		const basePath = `/dashboard/groups/${group?.id}`;

		if (itemPath === '') {
			return currentPath === basePath;
		}
		return currentPath === `${basePath}${itemPath}`;
	}

	const currentPageTitle = $derived.by(() => {
		const currentPath = $page.url.pathname;
		const basePath = `/dashboard/groups/${group?.id}`;

		const activeItem = menuItems.find((item) => {
			if (item.path === '') {
				return currentPath === basePath;
			}
			return currentPath.startsWith(`${basePath}${item.path}`);
		});

		return activeItem ? activeItem.i18nKey() : '';
	});
</script>

<div class="flex h-full w-full flex-col gap-4">
	<!-- Header Section -->
	<div class="flex flex-col gap-3">
		<div class="flex flex-row items-center gap-3">
			<h1 class="text-3xl font-bold">{group?.name}</h1>
			{#if currentPageTitle && !isActive('')}
				<span class="text-text/50">/</span>
				<span class="text-2xl text-text/70">{currentPageTitle}</span>
			{/if}
		</div>

		<!-- Navigation Tabs -->
		<nav class="flex flex-row gap-2 border-b border-text/20">
			{#each menuItems as item (item.path)}
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
			{/each}
		</nav>
	</div>

	<!-- Page Content -->
	<div class="flex-1 overflow-auto">
		{@render children?.()}
	</div>
</div>
