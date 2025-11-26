import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals, url }) => {
	if (locals.sessionUser) {
		if (url.searchParams.get('redirect')) {
			throw redirect(303, url.searchParams.get('redirect')!);
		}
		throw redirect(303, '/');
	}
};
