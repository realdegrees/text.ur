import { sessionStore } from '$lib/runes/session.svelte.js';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { membership, sessionUser } = await parent();
	sessionStore.validatePermissions(
		membership,
		['administrator'],
		`/dashboard/groups/${membership.group.id}/documents`
	);
	return { membership, sessionUser };
};
