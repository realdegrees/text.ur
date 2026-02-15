import { api } from '$api/client';
import type { Paginated } from '$api/pagination';
import type { MembershipRead } from '$api/types';
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
		throw new Error(`Failed to load memberships: ${result.error.detail}`);
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
