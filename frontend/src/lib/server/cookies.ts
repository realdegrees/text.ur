import type { Cookies } from '@sveltejs/kit';

/**
 * Forwards cookies from a backend response to the SvelteKit client.
 *
 * Uses `Headers.getSetCookie()` to correctly split individual
 * Set-Cookie headers without breaking on commas inside `Expires`
 * date values.
 */
export const forwardCookies = (response: Response, cookies: Cookies): void => {
	const cookieStrings = response.headers.getSetCookie();
	if (!cookieStrings.length) return;

	for (const cookieString of cookieStrings) {
		const [nameValue, ...attributes] = cookieString.split('; ');
		const [name, ...valueParts] = nameValue.split('=');
		// Rejoin in case the value itself contains '='
		const value = valueParts.join('=');

		const cookieOptions: any = { path: '/' };
		for (const attr of attributes) {
			const [key, val] = attr.split('=');
			const lowerKey = key.toLowerCase();
			if (lowerKey === 'httponly') cookieOptions.httpOnly = true;
			else if (lowerKey === 'secure') cookieOptions.secure = true;
			else if (lowerKey === 'samesite') cookieOptions.sameSite = val as any;
			else if (lowerKey === 'max-age') cookieOptions.maxAge = parseInt(val);
			else if (lowerKey === 'path') cookieOptions.path = val;
		}

		cookies.set(name, value, cookieOptions);
	}
};
