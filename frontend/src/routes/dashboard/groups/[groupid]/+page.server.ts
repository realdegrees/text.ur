import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ url }) => {
	return redirect(303, url.pathname + '/documents');
};
