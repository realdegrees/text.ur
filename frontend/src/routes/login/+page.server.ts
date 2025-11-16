import { redirect, fail, type Actions } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { api } from '$api/client';

export const load: PageServerLoad = async ({ locals }) => {
	if (locals.sessionUser) {
		throw redirect(303, '/');
	}
};

export const actions: Actions = {
	login: async ({ fetch, request }) => {
		const formData = await request.formData();
		const username = formData.get('username')?.toString();
		const password = formData.get('password')?.toString();

		if (!username || !password) {
			return fail(400, { error: 'Username/Email and password are required' });
		}

		const result = await api.post('/login', formData, { fetch });

		if (!result.success) {
			return fail(401, { error: 'Invalid username/email or password' });
		}

		throw redirect(303, '/');
	},

	register: async ({ fetch, request }) => {
		const formData = await request.formData();
		const username = formData.get('username')?.toString();
		const email = formData.get('email')?.toString();
		const password = formData.get('password')?.toString();
		const confirmPassword = formData.get('confirmPassword')?.toString();
		const firstName = formData.get('firstName')?.toString();
		const lastName = formData.get('lastName')?.toString();

		if (!username || !email || !password) {
			return fail(400, { error: 'Username, email, and password are required' });
		}

		if (password !== confirmPassword) {
			return fail(400, { error: 'Passwords do not match' });
		}

		await api.post(
			'/register',
			{
				username,
				email,
				password,
				first_name: firstName || undefined,
				last_name: lastName || undefined
			},
			{
				fetch
			}
		);

		return {
			success: true,
			message: 'Registration successful! Please check your email to verify your account.'
		};
	}
};
