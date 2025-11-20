import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ cookies }) => {
	// Get access token from httponly cookie (only accessible server-side)
	const accessToken = cookies.get('access_token');

	return {
		accessToken: accessToken || null
	};
};
