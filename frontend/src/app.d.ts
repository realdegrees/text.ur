// See https://svelte.dev/docs/kit/types#app.d.ts
import type { Locales } from '$i18n/i18n-types';
import type { UserPrivate } from '$api/types';
declare global {
	namespace App {
		// interface Error {}
		interface Locals {
			sessionUser?: UserPrivate;
			locale: Locales;
		}
		// interface PageData {}
		// interface PageState {}
		// interface Platform {}
	}
}

export {};
