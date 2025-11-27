import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals, params }) => {
	// Require authentication
	if (!locals.sessionUser) {
		throw redirect(303, `/login?redirect=/users/${params.userid}`);
	}

	// Only allow users to access their own settings page
	if (locals.sessionUser.id !== parseInt(params.userid)) {
		throw redirect(303, '/');
	}

	return locals;
};
