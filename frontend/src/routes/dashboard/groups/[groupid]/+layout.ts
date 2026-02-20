import { redirect } from '@sveltejs/kit';
import type { LayoutLoad } from './$types';
import { notification } from '$lib/stores/notificationStore';
import type { BreadcrumbItem } from '$types/breadcrumb';
import { api } from '$api/client';
import type { ScoreConfigRead } from '$api/types';

export const load: LayoutLoad = async ({ parent, params, fetch }) => {
	const data = await parent();
	const membership = data.routeMembership;
	if (!membership) {
		notification('error', 'You are not a member of this group.'); // TODO i18n
		throw redirect(303, '/dashboard');
	}

	// Fetch the group's score config (includes reactions list)
	const scoreConfigResult = await api.get<ScoreConfigRead>(
		`/groups/${params.groupid}/score-config`,
		{ fetch }
	);

	const scoreConfig = scoreConfigResult.success ? scoreConfigResult.data : null;

	return {
		...data,
		membership,
		scoreConfig,
		breadcrumbs: [
			{ label: 'Dashboard', href: '/dashboard' },
			{ label: membership.group.name }
		] satisfies BreadcrumbItem[]
	};
};
