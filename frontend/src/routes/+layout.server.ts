import { redirect } from '@sveltejs/kit';
import type { LayoutServerLoad } from './$types';

const noAuthRoutes = [
	'/login',
	'/',
];
export const load: LayoutServerLoad = async ({ locals, route }) => {
	// Redirect to login if no session user and not on a no-auth route
	if (!locals.sessionUser && !noAuthRoutes.includes(route.id || '')) {
		throw redirect(303, '/login');
	}
	return locals;
};
