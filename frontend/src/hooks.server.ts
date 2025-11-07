import { sequence } from '@sveltejs/kit/hooks';
import type { Handle, HandleFetch } from '@sveltejs/kit';
import { jwtDecode } from 'jwt-decode';
import { env } from '$env/dynamic/public';
import { loadAllLocales } from '$i18n/i18n-util.sync';
import { detectLocale } from '$i18n/i18n-util';
import { forwardCookies } from '$lib/server/cookies';

const baseUrl = env.PUBLIC_BACKEND_BASEURL;
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
		try {
			const refreshResponse = await fetch(`${baseUrl}/api/login/refresh`, {
				method: 'POST',
				headers: {
					Cookie: `refresh_token=${refreshToken}`
				}
			});

			if (refreshResponse.ok) {
				forwardCookies(refreshResponse, cookies);
			}
		} catch (e) {
			console.log('Failed to refresh token:', e);
		}
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
	} catch (e) {
		// Failed to fetch user, continue without user
		console.log('Unable to fetch user:', e);
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
 * Sets the translation based on the user's cookie.
 */
const translation: Handle = async ({ event, resolve }) => {
	// Load translations (only once per process)
	loadAllLocales();

	// Determine locale: from cookie or via detection fallback
	const locale = detectLocale(() => [event.cookies.get('locale') ?? '']);

	// Make it available in all load functions and hooks
	event.locals.locale = locale;
	event.cookies.set('locale', locale, { path: '/' });

	// Continue with SSR rendering
	const response = await resolve(event, {
		transformPageChunk: ({ html }) => html.replace('%lang%', locale) // optional: inject lang attr if you use a placeholder in <html lang="%lang%">
	});

	return response;
};

/**
 * Proxies requests starting with '/api' to the backend API.
 */
const apiProxy: Handle = ({ event, resolve }) => {
	const url = new URL(event.request.url);
	if (url.pathname.startsWith('/api')) event.request = withBaseUrl(event.request, baseUrl);
	return resolve(event);
};

export const handle = sequence(apiProxy, dark, translation, user);
