import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import type { BreadcrumbItem } from '$types/breadcrumb';

export const load: PageLoad = async ({ parent }) => {
	const { membership, sessionUser } = await parent();

	// Check if user is admin or owner
	const isAdmin = membership.permissions.includes('administrator') || membership.is_owner;

	if (!isAdmin) {
		throw redirect(302, `/dashboard/groups/${membership.group.id}/documents`);
	}

	return {
		membership,
		sessionUser,
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
