import { api } from '$api/client';
import type { Paginated } from '$api/pagination';
import type { DocumentRead, MembershipRead, ScoreRead } from '$api/types';
import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import type { BreadcrumbItem } from '$types/breadcrumb';

export const load: PageLoad = async ({ fetch, params, parent }) => {
	const { membership, scoreConfig } = await parent();

	const [memberResult, scoreResult, docsResult] = await Promise.all([
		api.get<MembershipRead>(`/groups/${params.groupid}/memberships/${params.userid}`, {
			fetch
		}),
		api.get<ScoreRead>(`/groups/${params.groupid}/memberships/${params.userid}/score`, {
			fetch
		}),
		api.get<Paginated<DocumentRead>>(`/documents?limit=100`, {
			fetch,
			filters: [{ field: 'group_id', operator: '==', value: params.groupid }],
			sort: [{ field: 'name', direction: 'asc' }]
		})
	]);

	if (!memberResult.success) {
		throw error(memberResult.error.status_code, memberResult.error.detail);
	}

	if (!scoreResult.success) {
		throw error(scoreResult.error.status_code, scoreResult.error.detail);
	}

	const member = memberResult.data;
	const username = member.user.username ?? 'Unknown';
	const documents = docsResult.success ? docsResult.data.data : [];

	return {
		member,
		score: scoreResult.data,
		documents,
		scoreConfig,
		breadcrumbs: [
			{ label: 'Dashboard', href: '/dashboard' },
			{
				label: membership.group.name,
				href: `/dashboard/groups/${membership.group.id}`
			},
			{
				label: 'Members',
				href: `/dashboard/groups/${membership.group.id}/memberships`
			},
			{ label: username }
		] satisfies BreadcrumbItem[]
	};
};
