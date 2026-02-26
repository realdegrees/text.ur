import { api } from '$api/client';
import type { Paginated } from '$api/pagination';
import type { MembershipRead } from '$api/types';
import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import type { BreadcrumbItem } from '$types/breadcrumb';

export const load: PageLoad = async ({ fetch, params, url, parent, depends }) => {
	depends('app:group-memberships');
	const { membership } = await parent();

	const result = await api.get<Paginated<MembershipRead>, 'group'>(
		`/memberships?${url.searchParams}`,
		{
			fetch,
			filters: [
				{
					field: 'group_id',
					operator: '==',
					value: params.groupid
				}
			]
		}
	);

	if (!result.success) {
		throw error(result.error.status_code, result.error.detail);
	}

	return {
		memberships: result.data,
		breadcrumbs: [
			{ label: 'Dashboard', href: '/dashboard' },
			{
				label: membership.group.name,
				href: `/dashboard/groups/${membership.group.id}`
			},
			{ label: 'Members' }
		] satisfies BreadcrumbItem[]
	};
};
