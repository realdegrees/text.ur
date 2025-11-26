import { browser } from '$app/environment';
import { env } from '$env/dynamic/public';
import type { Filter, Sort, AppError } from './types';
import type { Paginated } from './pagination';
import type { GetFilterModel, TypedFilter, ComputeExclusions } from './filters';
import { filterToSearchParam, sortToSearchParam } from '$lib/util/query';
import { appErrorSchema } from './schemas';

export type ApiResult<T> = { success: true; data?: T } | { success: false; error: AppError };
export type ApiGetResult<T> = { success: true; data: T } | { success: false; error: AppError };
export type ApiMutationResult = { success: true } | { success: false; error: AppError };
export type ApiCreateResult<T> = { success: true; data: T } | { success: false; error: AppError };

/**
 * Generate a unique connection ID for this browser session
 */
function generateConnectionId(): string {
	return `${Date.now()}-${Math.random().toString(36).substring(2, 15)}`;
}

interface FetchOptions extends Omit<RequestInit, 'body'> {
	fetch?: typeof fetch;
	filters?: readonly TypedFilter<any>[];
	sort?: Sort[];
	_isRetry?: boolean;
}

/**
 * API client configuration and fetch wrapper with automatic authentication and token refresh.
 * Cookies are handled automatically by the browser (credentials: 'include')
 * and forwarded by SvelteKit's handleFetch hook for SSR requests.
 */
class ApiClient {
	private baseUrl: string = env.PUBLIC_BACKEND_BASEURL;
	private connectionId: string = browser ? generateConnectionId() : '';
	private isRefreshing = false;

	/**
	 * Get the configured base URL.
	 */
	getBaseUrl(): string {
		return this.baseUrl;
	}

	/**
	 * Get the connection ID for this session
	 */
	getConnectionId(): string {
		return this.connectionId;
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
	 * Build URL with filters and sort parameters
	 */
	private buildUrl(input: string | URL | Request, options?: FetchOptions): string {
		let url: string;

		if (input instanceof Request) {
			url = this.resolveUrl(input.url);
		} else {
			url = this.resolveUrl(input);
		}

		const { filters, sort } = options || {};

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

			return urlObj.toString();
		}

		return url;
	}

	/**
	 * Parse response as JSON, handling empty responses
	 */
	private async parseResponse<T>(response: Response): Promise<T | undefined> {
		// Handle 204 No Content
		if (response.status === 204) {
			return undefined;
		}

		// Get response text
		const text = await response.text();

		// Handle empty responses (common for 200/201 with no body)
		if (!text || text.trim() === '') {
			return undefined;
		}

		// Try to parse as JSON
		try {
			return JSON.parse(text) as T;
		} catch (e) {
			// If content-type suggests JSON and we have content, it's a parse error
			const contentType = response.headers.get('content-type');
			if (contentType?.includes('application/json')) {
				console.error('Failed to parse JSON response:', text);
				throw new Error('Failed to parse JSON response');
			}
			// Otherwise, return undefined for non-JSON responses
			return undefined;
		}
	}

	/**
	 * Handle error response
	 */
	private async handleErrorResponse(response: Response): Promise<{ success: false; error: AppError }> {
		let json: any = null;

		try {
			json = await response.json();
			const errorData = appErrorSchema.safeParse(json);

			if (errorData.success) {
				return {
					success: false,
					error: errorData.data
				};
			}
		} catch {
			// JSON parse failed - fall through to generic error
		}

		// No JSON or parse failed - use response status text
		return {
			success: false,
			error: {
				error_code: 'unknown_error',
				detail: response.statusText || 'Request failed',
				status_code: response.status
			}
		};
	}

	/**
	 * Attempt to refresh the access token using the refresh_token cookie
	 */
	private async refreshToken(fetchFn: typeof fetch): Promise<boolean> {
		if (this.isRefreshing) {
			return false;
		}

		this.isRefreshing = true;

		try {
			const refreshUrl = this.resolveUrl('/login/refresh');
			const response = await fetchFn(refreshUrl, {
				method: 'POST',
				credentials: 'include'
			});

			return response.ok;
		} catch {
			return false;
		} finally {
			this.isRefreshing = false;
		}
	}

	/**
	 * Core fetch method with automatic token refresh on 401
	 */
	async fetch<T>(
		input: string | URL | Request,
		options?: FetchOptions & { body?: unknown }
	): Promise<ApiResult<T>> {
		if (!browser && !options?.fetch) {
			throw new Error(
				'API client requires a fetch function when used in server context. Pass event.fetch as the third argument.'
			);
		}

		const { fetch: fetchFnOverride, filters, sort, _isRetry, body, ...init } = options || {};
		const actualFetch = fetchFnOverride ?? fetch!;
		const url = this.buildUrl(input, { filters, sort });

		const requestInit: RequestInit = {
			...init,
			credentials: init.credentials || 'include',
			headers: {
				...init.headers,
				...(this.connectionId && { 'X-Connection-ID': this.connectionId })
			},
			body: body !== undefined ? (body instanceof FormData ? body : JSON.stringify(body)) : undefined
		};

		let response: Response;
		try {
			response = await actualFetch(url, requestInit);
		} catch (e) {
			return {
				success: false,
				error: {
					error_code: 'unknown_error',
					detail: e instanceof Error ? e.message : 'Network error',
					status_code: 0
				}
			};
		}

		// Handle 401 Unauthorized - attempt token refresh
		if (response.status === 401 && !_isRetry && !url.includes('/refresh')) {
			const refreshed = await this.refreshToken(actualFetch);

			if (refreshed) {
				// Retry the original request with refreshed token
				return this.fetch<T>(input, {
					...options,
					_isRetry: true
				});
			}
		}

		// Handle error responses
		if (!response.ok) {
			return this.handleErrorResponse(response);
		}

		// Parse successful response
		try {
			const data = await this.parseResponse<T>(response);
			return { success: true, data };
		} catch (e) {
			return {
				success: false,
				error: {
					error_code: 'unknown_error',
					detail: 'Failed to parse response',
					status_code: 500
				}
			};
		}
	}

	/**
	 * GET request wrapper with automatic authentication and type-safe filters.
	 */
	async get<
		T,
		TData = T extends Paginated<infer U, any> ? U : T,
		TExclude extends keyof TData = never,
		TFilter = GetFilterModel<TData>,
		TFilters extends readonly TypedFilter<TFilter>[] = readonly TypedFilter<TFilter>[]
	>(
		input: string | URL,
		options?: FetchOptions
	): Promise<
		ApiGetResult<
			T extends Paginated<infer U, any>
				? Paginated<U, (ComputeExclusions<TFilter, TFilters> | TExclude) & PropertyKey>
				: T
		>
	> {
		const result = await this.fetch<T>(input, {
			...options,
			method: 'GET'
		});

		if (!result.success) {
			return result as any;
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
			data: result.data as any
		};
	}

	/**
	 * Download a file (GET) and return the response as an ArrayBuffer.
	 */
	async download(
		input: string | URL,
		options?: FetchOptions
	): Promise<ApiGetResult<ArrayBuffer>> {
		if (!browser && !options?.fetch) {
			throw new Error(
				'API client requires a fetch function when used in server context. Pass event.fetch as the third argument.'
			);
		}

		const { fetch: fetchFnOverride, _isRetry, ...init } = options || {};
		const actualFetch = fetchFnOverride ?? fetch!;
		const url = this.buildUrl(input);

		const requestInit: RequestInit = {
			...init,
			method: 'GET',
			credentials: init.credentials || 'include'
		};

		let response: Response;
		try {
			response = await actualFetch(url, requestInit);
		} catch (e) {
			return {
				success: false,
				error: {
					error_code: 'unknown_error',
					detail: e instanceof Error ? e.message : 'Network error',
					status_code: 0
				}
			};
		}

		// Handle 401 Unauthorized - attempt token refresh
		if (response.status === 401 && !_isRetry) {
			const refreshed = await this.refreshToken(actualFetch);

			if (refreshed) {
				return this.download(input, {
					...options,
					_isRetry: true
				});
			}
		}

		if (!response.ok) {
			return this.handleErrorResponse(response);
		}

		const arrayBuffer = await response.arrayBuffer();
		return { success: true, data: arrayBuffer };
	}

	/**
	 * POST request wrapper for creating resources with automatic JSON headers.
	 */
	async post<T>(
		input: string | URL,
		body?: unknown,
		options?: FetchOptions
	): Promise<ApiCreateResult<T | undefined>> {
		const isFormData = body instanceof FormData;

		const result = await this.fetch<T>(input, {
			...options,
			method: 'POST',
			headers: {
				...(isFormData ? {} : { 'Content-Type': 'application/json' }),
				...options?.headers
			},
			body
		});

		if (!result.success) {
			return result as any;
		}

		return { success: true, data: result.data };
	}

	/**
	 * PUT request wrapper for updating resources with automatic JSON headers.
	 */
	async update(
		input: string | URL,
		body?: unknown,
		options?: FetchOptions
	): Promise<ApiMutationResult> {
		const result = await this.fetch<void>(input, {
			...options,
			method: 'PUT',
			headers: {
				'Content-Type': 'application/json',
				...options?.headers
			},
			body
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
		options?: FetchOptions
	): Promise<ApiMutationResult> {
		const result = await this.fetch<void>(input, {
			...options,
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
