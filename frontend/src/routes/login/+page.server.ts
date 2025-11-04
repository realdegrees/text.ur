import { redirect, fail, type Actions } from "@sveltejs/kit";
import type { PageServerLoad } from "./$types";
import { forwardCookies } from "$lib/server/cookies";

export const load: PageServerLoad = async ({ locals }) => {
	if (locals.sessionUser) {
		throw redirect(303, "/");
	}
};

export const actions: Actions = {
	login: async ({ request, fetch, cookies }) => {
		const formData = await request.formData();
		const username = formData.get("username")?.toString();
		const password = formData.get("password")?.toString();

		if (!username || !password) {
			return fail(400, { error: "Username/Email and password are required" });
		}

		const loginFormData = new URLSearchParams();
		loginFormData.append("username", username);
		loginFormData.append("password", password);

		const response = await fetch("/api/login", {
			method: "POST",
			headers: {
				"Content-Type": "application/x-www-form-urlencoded"
			},
			body: loginFormData.toString()
		});

		if (!response.ok) {
			const error = await response.json().catch(() => ({ detail: "Login failed" }));
			return fail(response.status, { error: error.detail || "Invalid credentials" });
		}

		forwardCookies(response, cookies);

		throw redirect(303, "/");
	},

	register: async ({ request, fetch }) => {
		const formData = await request.formData();
		const username = formData.get("username")?.toString();
		const email = formData.get("email")?.toString();
		const password = formData.get("password")?.toString();
		const confirmPassword = formData.get("confirmPassword")?.toString();
		const firstName = formData.get("firstName")?.toString();
		const lastName = formData.get("lastName")?.toString();

		if (!username || !email || !password) {
			return fail(400, { error: "Username, email, and password are required" });
		}

		if (password !== confirmPassword) {
			return fail(400, { error: "Passwords do not match" });
		}

		const response = await fetch("/api/register", {
			method: "POST",
			headers: {
				"Content-Type": "application/json"
			},
			body: JSON.stringify({
				username,
				email,
				password,
				first_name: firstName || undefined,
				last_name: lastName || undefined
			})
		});

		if (!response.ok) {
			const error = await response.json().catch(() => ({ detail: "Registration failed" }));
			return fail(response.status, { error: error.detail || "Registration failed" });
		}

		return {
			success: true,
			message: "Registration successful! Please check your email to verify your account."
		};
	}
};
