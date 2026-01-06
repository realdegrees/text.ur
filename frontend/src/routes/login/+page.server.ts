import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals, url }) => {
	if (locals.sessionUser) {
		// Preserve verified param when redirecting authenticated users
		const verified = url.searchParams.get('verified');
		const redirectParam = url.searchParams.get('redirect');

		if (redirectParam) {
			const redirectUrl = verified ? `${redirectParam}?verified=true` : redirectParam;
			throw redirect(303, redirectUrl);
		}

		const dashboardUrl = verified ? '/dashboard?verified=true' : '/dashboard';
		throw redirect(303, dashboardUrl);
	}
};
