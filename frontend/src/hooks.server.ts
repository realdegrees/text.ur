import { type Handle } from '@sveltejs/kit';
import { sequence } from '@sveltejs/kit/hooks';
import type { HandleFetch } from '@sveltejs/kit';
import { jwtDecode } from 'jwt-decode';
import { env } from '$env/dynamic/public';

const baseUrl = env.PUBLIC_API_URL;
const withBaseUrl = (request: Request, baseUrl: string): Request => {
	const url = new URL(request.url);
	return new Request(`${baseUrl}${url.pathname}${url.search}`, request);
};

const isTokenExpired = (token: string | undefined): boolean => {
	if (!token) return true;
	try {
		const decoded = jwtDecode(token);
		return !decoded.exp || decoded.exp * 1000 <= Date.now();
	} catch {
		return true;
	}
};

/**
 * Handles automatic token refresh when the access token is expired.
 */
export const handleFetch: HandleFetch = async ({
	event: { cookies, getClientAddress },
	request,
	fetch
}) => {
	const existingHeader = request.headers.get('x-forwarded-for');
	if (existingHeader) {
		request.headers.set('x-forwarded-for', `${getClientAddress()}, ${existingHeader}`);
	} else {
		request.headers.set('x-forwarded-for', getClientAddress());
	}

	const url = new URL(request.url);

	if (!url.pathname.startsWith('/api')) {
		return fetch(request);
	}

	request = withBaseUrl(request, baseUrl);

	const accessToken = cookies.get('access_token');
	const refreshToken = cookies.get('refresh_token');

	if (isTokenExpired(accessToken) && !isTokenExpired(refreshToken)) {
		await fetch(`${baseUrl}/api/login/refresh`, {
			method: 'POST'
		});
	}

	return fetch(request);
};

/**
 * Fetches the user info from the backend and attaches it to the SvelteKit session store.
 */
const user: Handle = async ({ event, resolve }) => {
	if (event.url.pathname.startsWith('/api')) return resolve(event);

	const accessToken = event.cookies.get('access_token');
	const refreshToken = event.cookies.get('refresh_token');

	if (!accessToken && !refreshToken) return resolve(event);

	try {
		const userResponse = await event.fetch(`${baseUrl}/api/users/me`);
		if (userResponse.ok) {
			event.locals.sessionUser = await userResponse.json();
		}
	} catch {
		// Failed to fetch user, continue without user
	}

	return resolve(event);
};
/**
 * Sets the dark mode based on the user's cookie.
 */
const dark: Handle = ({ event, resolve }) => {
	const theme = event.cookies.get('theme');
	if (theme) {
		return resolve(event, {
			transformPageChunk: ({ html }) =>
				theme === 'light' ? html.replace('class="dark"', '') : html
		});
	}
	return resolve(event);
};

/**
 * Proxies requests starting with '/api' to the backend API.
 */
const apiProxy: Handle = ({ event, resolve }) => {
	const url = new URL(event.request.url);
	if (url.pathname.startsWith('/api')) event.request = withBaseUrl(event.request, baseUrl);
	return resolve(event);
};

export const handle = sequence(apiProxy, dark, user);
