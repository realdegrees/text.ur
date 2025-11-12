import { jwtDecode } from 'jwt-decode';
import { browser } from '$app/environment';
import { error } from '@sveltejs/kit';
import { env } from '$env/dynamic/public';
import type { Filter, Sort } from './types';
import { filterToSearchParam, sortToSearchParam } from '$lib/util/query';


/**
 * Token storage and management for client-side authentication.
 */
class TokenManager {
	private accessTokenKey = 'access_token';
	private refreshTokenKey = 'refresh_token';

	getAccessToken(): string | null {
		if (!browser) return null;
		return this.getCookie(this.accessTokenKey);
	}

	getRefreshToken(): string | null {
		if (!browser) return null;
		return this.getCookie(this.refreshTokenKey);
	}

	private getCookie(name: string): string | null {
		if (!browser) return null;
		const value = `; ${document.cookie}`;
		const parts = value.split(`; ${name}=`);
		if (parts.length === 2) {
			return parts.pop()?.split(';').shift() || null;
		}
		return null;
	}

	isTokenExpired(token: string | null): boolean {
		if (!token) return true;
		try {
			const decoded = jwtDecode(token);
			return !decoded.exp || decoded.exp * 1000 <= Date.now();
		} catch {
			return true;
		}
	}
}

/**
 * API client configuration and fetch wrapper with automatic authentication.
 */
class ApiClient {
	private baseUrl: string = env.PUBLIC_BACKEND_BASEURL;
	private tokenManager = new TokenManager();
	private refreshPromise: Promise<void> | null = null;

	/**
	 * Get the configured base URL.
	 */
	getBaseUrl(): string {
		return this.baseUrl;
	}

	/**
	 * Resolve a relative or absolute URL against the configured base URL.
	 */
	private resolveUrl(url: string | URL): string {
		if (url instanceof URL) {
			return url.toString();
		}

		if (url.startsWith('http://') || url.startsWith('https://')) {
			return url;
		}

		let path = url.startsWith('/') ? url : `/${url}`;

		if (!path.startsWith('/api/')) {
			path = `/api${path}`;
		}

		return `${this.baseUrl}${path}`;
	}

	/**
	 * Refresh the access token using the refresh token.
	 */
	private async refreshAccessToken(): Promise<void> {
		const refreshToken = this.tokenManager.getRefreshToken();

		if (!refreshToken || this.tokenManager.isTokenExpired(refreshToken)) {
			throw new Error('No valid refresh token available');
		}

		const response = await fetch(`${this.baseUrl}/api/login/refresh`, {
			method: 'POST',
			credentials: 'include'
		});

		if (!response.ok) {
			throw new Error('Failed to refresh access token');
		}
	}

	/**
	 * Ensure we have a valid access token before making a request.
	 */
	private async ensureValidToken(): Promise<void> {
		const accessToken = this.tokenManager.getAccessToken();
		const refreshToken = this.tokenManager.getRefreshToken();

		if (
			this.tokenManager.isTokenExpired(accessToken) &&
			!this.tokenManager.isTokenExpired(refreshToken)
		) {
			if (!this.refreshPromise) {
				this.refreshPromise = this.refreshAccessToken().finally(() => {
					this.refreshPromise = null;
				});
			}
			await this.refreshPromise;
		}
	}

	/**
	 * Fetch wrapper with automatic authentication and base URL resolution.
	 */
	async fetch<T>(
		input: string | URL | Request,
		init?: RequestInit & {
			fetch?: typeof fetch;
			filters?: (Filter | undefined)[];
			sort?: Sort[];
		}
	): Promise<T> {
		if (!browser && !init?.fetch) {
			throw new Error(
				'API client requires a fetch function when used in server context. Pass event.fetch as the third argument.'
			);
		}
		
		const { fetch: fetchFnOverride, filters, sort, ...cleanedInit } = init || {};

		const actualFetch = fetchFnOverride ?? fetch!;

		let url: string;
		
		if (input instanceof Request) {
			url = this.resolveUrl(input.url);			
		} else {
			url = this.resolveUrl(input);			
		}

		// Append filters and sort parameters to the URL
		if ((filters && filters.length > 0) || (sort && sort.length > 0)) {
			const urlObj = new URL(url);
			
			if (filters && filters.length > 0) {
				filters.forEach((filter) => {
					if (filter) {
						const { key, value } = filterToSearchParam(filter);
						urlObj.searchParams.append(key, value);
					}
				});
			}
			
			if (sort && sort.length > 0) {
				sort.forEach((sortItem) => {
					const { key, value } = sortToSearchParam(sortItem);
					urlObj.searchParams.append(key, value);
				});
			}
			
			url = urlObj.toString();
		}

		if (browser) {
			try {
				await this.ensureValidToken();
			} catch (e) {
				console.log('Failed to refresh token:', e);
			}
		}

		const requestInit: RequestInit = {
			...cleanedInit,
			credentials: cleanedInit.credentials || 'include'
		};

		
		const response = await actualFetch(url, requestInit);

		if (!response.ok) {
			error(response.status, `API request failed: ${response.statusText}`);
		}

		return response.json() as Promise<T>;
	}
}

const api = new ApiClient();

export { api };
