import { api } from '$api/client';
import { error, redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import type { ShareLinkRead } from '$api/types';

export const load: PageServerLoad = async ({ locals, params, fetch }) => {
	const { sessionUser } = locals;
	const { token } = params;

	// If user is authenticated, create membership via access endpoint
	if (sessionUser) {
		// Adds the user to the group if not already a member
		const response = await api.post<ShareLinkRead>(`/api/sharelinks/use/${token}`, {}, { fetch });

		if (response.success && response.data) {
			// Membership created or user is already a member - redirect to dashboard
			throw redirect(303, '/dashboard/groups/' + response.data.group_id + '/documents');
		} else {
			throw error(400, 'Failed to join group via share link.');
		}
	}

	// User is not authenticated - show anonymous registration form
	return {
		token,
		requiresAnonymousRegistration: true
	};
};
