import { jwtDecode } from 'jwt-decode';
import { browser } from '$app/environment';
import { error } from '@sveltejs/kit';
import { env } from '$env/dynamic/public';
import type { Filter, Sort, AppError } from './types';
import type { Paginated } from './pagination';
import type { GetFilterModel, TypedFilter, ComputeExclusions } from './filters';
import { filterToSearchParam, sortToSearchParam } from '$lib/util/query';
import { appErrorCodeSchema, appErrorSchema } from './schemas';

export type ApiResult<T> = 
	| { success: true; data?: T }
	| { success: false; error: AppError };

export type ApiGetResult<T> = 
	| { success: true; data: T }
	| { success: false; error: AppError };

export type ApiMutationResult = 
	| { success: true }
	| { success: false; error: AppError };

export type ApiCreateResult<T> = 
	| { success: true; data: T }
	| { success: false; error: AppError };

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
	 * Fetch wrapper with automatic authentication and type-safe filters.
	 * Returns a type-safe result object with success/error discrimination.
	 * 
	 * When fetching Paginated<T> with filters, the return type automatically
	 * excludes fields based on the active filters.
	 * You can also explicitly provide a field to exclude by passing a second
	 * generic.
	 */
	// Overload A: caller provides Paginated<T> and explicit TExclude, e.g. api.fetch<Paginated<MembershipRead>, 'group'>
	fetch<
		T extends Paginated<any>,
		TExclude extends keyof (T extends Paginated<infer U, any> ? U : never) = never,
		TFilter = GetFilterModel<T extends Paginated<infer U, any> ? U : never>,
		TFilters extends readonly TypedFilter<TFilter>[] = readonly TypedFilter<TFilter>[]
	>(
		input: string | URL | Request,
		init?: RequestInit & {
			fetch?: typeof fetch;
			filters?: TFilters;
			sort?: Sort[];
		}
	): Promise<ApiResult<
		T extends Paginated<infer U, any>
			? Paginated<
				  U,
				  (ComputeExclusions<TFilter, TFilters> | TExclude) & PropertyKey
			  >
			: T
	>>;

	// Overload B: explicit TData between T and TExclude for advanced callers
	fetch<
		T,
		TData = T extends Paginated<infer U, any> ? U : T,
		TExclude extends keyof TData = never,
		TFilter = GetFilterModel<TData>,
		TFilters extends readonly TypedFilter<TFilter>[] = readonly TypedFilter<TFilter>[]
	>(
		input: string | URL | Request,
		init?: RequestInit & {
			fetch?: typeof fetch;
			filters?: TFilters;
			sort?: Sort[];
		}
	): Promise<ApiResult<
		T extends Paginated<infer U, any>
			? Paginated<
				  U,
				  (ComputeExclusions<TFilter, TFilters> | TExclude) & PropertyKey
			  >
			: T
	>>;

	// Implementation of fetch: compute TData first to enable inference
	async fetch<
		T,
		TData = T extends Paginated<infer U, any> ? U : T,
		TExclude extends keyof TData = never,
		TFilter = GetFilterModel<TData>,
		TFilters extends readonly TypedFilter<TFilter>[] = readonly TypedFilter<TFilter>[]
	>(
		input: string | URL | Request,
		init?: RequestInit & {
			fetch?: typeof fetch;
			filters?: TFilters;
			sort?: Sort[];
		}
	): Promise<ApiResult<
		T extends Paginated<infer U, any>
			? Paginated<
				  U,
				  (ComputeExclusions<TFilter, TFilters> | TExclude) & PropertyKey
			  >
			: T
	>> {
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
						const { key, value } = filterToSearchParam(filter as Filter);
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
			const json = await response.json();
			const errorData = appErrorSchema.safeParse(json);

			if (errorData.success) {
				return {
					success: false,
					error: errorData.data
				};
			}else {
				console.error("Unmapped Error", json);
				
				return {
					success: false,
					error: {
						error_code: 'unknown_error',
						detail: response.statusText,
						status_code: response.status
					}
				}
			}
		}

		let contentType: string | null = null;
		try {
			contentType = response.headers.get("content-type");
		} catch {
			// In server-side context, headers might be filtered
		}
		
		const hasJsonContent = contentType && contentType.includes("application/json");
		
		if (response.status === 204) {
			return { 
				success: true, 
				data: undefined
			};
		}

		// Try to parse as JSON (even if content-type is wrong or unavailable)
		try {
			const data = await response.json() as (
				T extends Paginated<infer U, any>
					? Paginated<U, (ComputeExclusions<TFilter, TFilters> | TExclude) & PropertyKey>
					: T
			);
			
			return { success: true, data };
		} catch (e) {
			// If we explicitly know it's not JSON and parsing failed, return undefined
			if (contentType && !hasJsonContent) {
				return { 
					success: true, 
					data: undefined
				};
			}
			// Otherwise, it's an error
			return { 
				success: true, 
				data: undefined
			};
		}
	}

	/**
	 * GET request wrapper with automatic authentication and type-safe filters.
	 */
	get<
		T extends Paginated<any>,
		TExclude extends keyof (T extends Paginated<infer U, any> ? U : never) = never,
		TFilter = GetFilterModel<T extends Paginated<infer U, any> ? U : never>,
		TFilters extends readonly TypedFilter<TFilter>[] = readonly TypedFilter<TFilter>[]
	>(
		input: string | URL,
		init?: Omit<RequestInit, 'method' | 'body'> & {
			fetch?: typeof fetch;
			filters?: TFilters;
			sort?: Sort[];
		}
	): Promise<ApiGetResult<
		T extends Paginated<infer U, any>
			? Paginated<
				  U,
				  (ComputeExclusions<TFilter, TFilters> | TExclude) & PropertyKey
			  >
			: T
	>>;

	get<
		T,
		TData = T extends Paginated<infer U, any> ? U : T,
		TExclude extends keyof TData = never,
		TFilter = GetFilterModel<TData>,
		TFilters extends readonly TypedFilter<TFilter>[] = readonly TypedFilter<TFilter>[]
	>(
		input: string | URL,
		init?: Omit<RequestInit, 'method' | 'body'> & {
			fetch?: typeof fetch;
			filters?: TFilters;
			sort?: Sort[];
		}
	): Promise<ApiGetResult<
		T extends Paginated<infer U, any>
			? Paginated<
				  U,
				  (ComputeExclusions<TFilter, TFilters> | TExclude) & PropertyKey
			  >
			: T
	>>;

	async get<
		T,
		TData = T extends Paginated<infer U, any> ? U : T,
		TExclude extends keyof TData = never,
		TFilter = GetFilterModel<TData>,
		TFilters extends readonly TypedFilter<TFilter>[] = readonly TypedFilter<TFilter>[]
	>(
		input: string | URL,
		init?: Omit<RequestInit, 'method' | 'body'> & {
			fetch?: typeof fetch;
			filters?: TFilters;
			sort?: Sort[];
		}
	): Promise<ApiGetResult<
		T extends Paginated<infer U, any>
			? Paginated<
				  U,
				  (ComputeExclusions<TFilter, TFilters> | TExclude) & PropertyKey
			  >
			: T
	>> {
		const result = await this.fetch<T, TData, TExclude, TFilter, TFilters>(input, {
			...init,
			method: 'GET'
		});
		
		if (!result.success) {
			return result;
		}
		
		if (result.data === undefined) {
			return {
				success: false,
				error: {
					error_code: 'unknown_error',
					detail: 'GET request returned no data',
					status_code: 500
				}
			};
		}
		
		return {
			success: true,
			data: result.data as T extends Paginated<infer U, any>
				? Paginated<U, (ComputeExclusions<TFilter, TFilters> | TExclude) & PropertyKey>
				: T
		};
	}

	/**
	 * POST request wrapper for creating resources with automatic JSON headers.
	 */
	async post<T>(
		input: string | URL,
		body?: unknown,
		init?: Omit<RequestInit, 'method' | 'body'> & {
			fetch?: typeof fetch;
		}
	): Promise<ApiCreateResult<T>> {
		const isFormData = body instanceof FormData;

		const result = await this.fetch<T>(input, {
			...init,
			method: 'POST',
			headers: {
				// Only set JSON headers if not sending FormData
				...(isFormData ? {} : { 'Content-Type': 'application/json' }),
				...init?.headers
			},
			// Send FormData as-is, otherwise stringify the body
			body: isFormData ? (body as FormData) : body ? JSON.stringify(body) : undefined
		});
		
		if (!result.success) {
			return result;
		}
		
		if (result.data === undefined) {
			return {
				success: false,
				error: {
					error_code: 'unknown_error',
					detail: 'POST request returned no data',
					status_code: 500
				}
			};
		}
		
		return { success: true, data: result.data as T };
	}

	/**
	 * PUT request wrapper for updating resources with automatic JSON headers.
	 */
	async update(
		input: string | URL,
		body?: unknown,
		init?: Omit<RequestInit, 'method' | 'body'> & {
			fetch?: typeof fetch;
		}
	): Promise<ApiMutationResult> {
		const result = await this.fetch<void>(input, {
			...init,
			method: 'PUT',
			headers: {
				'Content-Type': 'application/json',
				...init?.headers
			},
			body: body ? JSON.stringify(body) : undefined
		});
		
		if (result.success) {
			return { success: true };
		}
		return result;
	}

	/**
	 * DELETE request wrapper with automatic authentication.
	 */
	async delete(
		input: string | URL,
		init?: Omit<RequestInit, 'method' | 'body'> & {
			fetch?: typeof fetch;
		}
	): Promise<ApiMutationResult> {
		const result = await this.fetch<void>(input, {
			...init,
			method: 'DELETE'
		});
		
		if (result.success) {
			return { success: true };
		}
		return result;
	}
}

const api = new ApiClient();

export { api };
