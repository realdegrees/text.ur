import { api } from '$api/client';
import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import type { ShareLinkReadFromToken } from '$api/types';

export const load: PageLoad = async ({ params, fetch }) => {
	const { token } = params;

	const sharelinkResponse = await api.get<ShareLinkReadFromToken>(`/api/sharelinks/${token}`, { fetch });
	if (!sharelinkResponse.success || !sharelinkResponse.data) {
		throw error(404, 'Share link not found or has expired.');
	}

	// User is not authenticated - show anonymous registration form
	return {
		shareLink: sharelinkResponse.data,
		requiresAnonymousRegistration: true
	};
};
