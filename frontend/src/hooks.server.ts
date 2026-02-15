import { sequence } from '@sveltejs/kit/hooks';
import type { Handle, HandleFetch } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';
import { loadAllLocales } from '$i18n/i18n-util.sync';
import { detectLocale } from '$i18n/i18n-util';
import { userCache } from '$lib/server/cache';
import { forwardCookies } from '$lib/server/cookies';

const baseUrl = env.INTERNAL_BACKEND_BASEURL;
const withBaseUrl = (request: Request, baseUrl: string): Request => {
	const url = new URL(request.url);
	return new Request(`${baseUrl}${url.pathname}${url.search}`, request);
};

/**
 * Forwards API requests to the backend and sets x-forwarded-for headers.
 * Also forwards cookies from the client request to the backend.
 * Automatically handles token refresh on 401 responses.
 */
export const handleFetch: HandleFetch = async ({ request, fetch, event }) => {
	const url = new URL(request.url);

	if (!url.pathname.startsWith('/api')) {
		return fetch(request);
	}

	request = withBaseUrl(request, baseUrl);

	// Forward cookies from the client to the backend
	let accessToken = event.cookies.get('access_token');
	const refreshToken = event.cookies.get('refresh_token');

	const headers = new Headers(request.headers);

	// Forward IP-related headers from the original client request
	const forwardedFor = event.request.headers.get('X-Forwarded-For');
	const realIp = event.request.headers.get('X-Real-IP');
	const forwardedProto = event.request.headers.get('X-Forwarded-Proto');
	const forwardedHost = event.request.headers.get('X-Forwarded-Host');

	if (forwardedFor) {
		headers.set('X-Forwarded-For', forwardedFor);
	} else {
		// Fall back to adapter-node's resolved client address when no
		// X-Forwarded-For header was passed through (e.g. internal routing)
		try {
			headers.set('X-Forwarded-For', event.getClientAddress());
		} catch {
			// getClientAddress() throws if ADDRESS_HEADER is not configured
		}
	}
	if (realIp) headers.set('X-Real-IP', realIp);
	if (forwardedProto) headers.set('X-Forwarded-Proto', forwardedProto);
	if (forwardedHost) headers.set('X-Forwarded-Host', forwardedHost);

	if (accessToken || refreshToken) {
		const cookieHeader = [
			accessToken ? `access_token=${accessToken}` : '',
			refreshToken ? `refresh_token=${refreshToken}` : ''
		]
			.filter(Boolean)
			.join('; ');

		headers.set('Cookie', cookieHeader);
	}

	// Buffer the body so it can be replayed on 401 retry
	const bodyBuffer =
		request.method !== 'GET' && request.method !== 'HEAD' && request.body
			? await request.arrayBuffer()
			: null;

	request = new Request(request.url, {
		method: request.method,
		headers,
		body: bodyBuffer
	} as RequestInit);

	let response = await fetch(request);

	// Handle 401 Unauthorized - attempt token refresh
	if (response.status === 401 && !url.pathname.includes('/refresh') && refreshToken) {
		// Try to refresh the token
		const refreshUrl = `${baseUrl}/api/login/refresh`;
		const refreshHeaders = new Headers();
		refreshHeaders.set('Cookie', `refresh_token=${refreshToken}`);

		const refreshResponse = await fetch(refreshUrl, {
			method: 'POST',
			headers: refreshHeaders,
			credentials: 'include'
		});

		if (refreshResponse.ok) {
			// Forward new cookies from refresh response to client
			forwardCookies(refreshResponse, event.cookies);

			// Get the updated access token
			accessToken = event.cookies.get('access_token');

			// Retry the original request with the new access token
			if (accessToken) {
				const retryHeaders = new Headers(request.headers);
				const cookieHeader = [`access_token=${accessToken}`, `refresh_token=${refreshToken}`].join(
					'; '
				);
				retryHeaders.set('Cookie', cookieHeader);

				const retryRequest = new Request(request.url, {
					method: request.method,
					headers: retryHeaders,
					body: bodyBuffer
				} as RequestInit);

				response = await fetch(retryRequest);
			}
		}
	}

	return response;
};

/**
 * Fetches the user info from the backend and attaches it to the SvelteKit session store.
 */
/** Allow ETag and Cache-Control headers to pass through to universal load functions during SSR. */
const serializeOptions = {
	filterSerializedResponseHeaders: (name: string) =>
		['etag', 'cache-control'].includes(name.toLowerCase())
};

const user: Handle = async ({ event, resolve }) => {
	if (event.url.pathname.startsWith('/api')) return resolve(event); // Only needed for server side requests

	const accessToken = event.cookies.get('access_token');

	// Check TTL cache first (keyed by access token)
	if (accessToken) {
		const cached = userCache.get(accessToken) as typeof event.locals.sessionUser;
		if (cached) {
			event.locals.sessionUser = cached;
			return resolve(event, serializeOptions);
		}
	}

	try {
		const userResponse = await event.fetch(`${baseUrl}/api/users/me`);
		if (userResponse.ok) {
			const userData = await userResponse.json();
			event.locals.sessionUser = userData;
			if (accessToken) {
				userCache.set(accessToken, userData);
			}
		}
	} catch (e) {
		// Failed to fetch user, continue without user
		console.log('Unable to fetch user:', e);
	}

	return resolve(event, serializeOptions);
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
	event.cookies.set('locale', locale, {
		path: '/',
		httpOnly: false, // Allow client-side access for language switching
		sameSite: 'lax',
		maxAge: 60 * 60 * 24 * 365 // 1 year
	});

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

const securityHeaders: Handle = async ({ event, resolve }) => {
	const response = await resolve(event);
	response.headers.set('Strict-Transport-Security', 'max-age=31536000; includeSubDomains; preload');
	response.headers.set('X-Frame-Options', 'DENY');
	response.headers.set('X-Content-Type-Options', 'nosniff');
	response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
	response.headers.set(
		'Permissions-Policy',
		'accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()'
	);
	return response;
};

export const handle = sequence(securityHeaders, apiProxy, dark, translation, user);
