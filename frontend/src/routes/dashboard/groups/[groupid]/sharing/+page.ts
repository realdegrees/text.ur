import { api } from '$api/client';
import type { Paginated } from '$api/pagination';
import type { ShareLinkRead } from '$api/types';
import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent, params, fetch }) => {
	const { membership, sessionUser } = await parent();

	// Check permissions directly (don't use sessionStore in load functions - it's for components only)
	const isAdmin = membership.permissions.includes('administrator') || membership.is_owner;
	const canManageShareLinks = membership.permissions.includes('manage_share_links');

	if (!isAdmin && !canManageShareLinks) {
		throw redirect(302, `/dashboard/groups/${membership.group.id}/documents`);
	}

	// Query share links for this group
	const shareLinkResult = await api.get<Paginated<ShareLinkRead>, 'group'>(
		`/groups/${params.groupid}/sharelinks`,
		{
			fetch
		}
	);

	if (!shareLinkResult.success) {
		throw new Error(`Failed to load share links: ${shareLinkResult.error.detail}`);
	}

	return { membership, sessionUser, shareLinks: shareLinkResult.data };
};
