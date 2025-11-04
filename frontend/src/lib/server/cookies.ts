import type { Cookies } from "@sveltejs/kit";

/**
 * Forwards cookies from a backend response to the SvelteKit client.
 */
export const forwardCookies = (response: Response, cookies: Cookies): void => {
	const setCookieHeader = response.headers.get("set-cookie");
	if (!setCookieHeader) return;

	const cookieStrings = setCookieHeader.split(", ");
	for (const cookieString of cookieStrings) {
		const [nameValue, ...attributes] = cookieString.split("; ");
		const [name, value] = nameValue.split("=");

		const cookieOptions: any = { path: "/" };
		for (const attr of attributes) {
			const [key, val] = attr.split("=");
			const lowerKey = key.toLowerCase();
			if (lowerKey === "httponly") cookieOptions.httpOnly = true;
			else if (lowerKey === "secure") cookieOptions.secure = true;
			else if (lowerKey === "samesite") cookieOptions.sameSite = val as any;
			else if (lowerKey === "max-age") cookieOptions.maxAge = parseInt(val);
			else if (lowerKey === "path") cookieOptions.path = val;
		}

		cookies.set(name, value, cookieOptions);
	}
};
