import type { PageLoad } from './$types';
import { error } from '@sveltejs/kit';

export const load: PageLoad = async ({ params, fetch, url }) => {
	const membersRes = await fetch(`/groups/${params.groupid}/memberships?${url.searchParams}`);
	if (!membersRes.ok) throw error(membersRes.status, 'Failed to load memberships');
	const memberships = await membersRes.json();

	return { memberships };
};
