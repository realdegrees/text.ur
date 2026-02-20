import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import type { BreadcrumbItem } from '$types/breadcrumb';
import { api } from '$api/client';
import type { ScoreConfigRead } from '$api/types';

export const load: PageLoad = async ({ parent, params, fetch }) => {
	const { membership, sessionUser } = await parent();

	// Check if user is admin or owner
	const isAdmin = membership.permissions.includes('administrator') || membership.is_owner;

	if (!isAdmin) {
		throw redirect(302, `/dashboard/groups/${membership.group.id}/documents`);
	}

	const scoreConfigResult = await api.get<ScoreConfigRead>(
		`/groups/${params.groupid}/score-config`,
		{ fetch }
	);

	return {
		membership,
		sessionUser,
		scoreConfig: scoreConfigResult.success ? scoreConfigResult.data : null,
		breadcrumbs: [
			{ label: 'Dashboard', href: '/dashboard' },
			{
				label: membership.group.name,
				href: `/dashboard/groups/${membership.group.id}`
			},
			{ label: 'Settings' }
		] satisfies BreadcrumbItem[]
	};
};
