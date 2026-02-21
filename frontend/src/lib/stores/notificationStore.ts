import type { Component } from 'svelte';
import type { SVGAttributes } from 'svelte/elements';
import { writable } from 'svelte/store';
import Success from '~icons/line-md/confirm-square-twotone';
import Error from '~icons/line-md/alert-square-twotone-loop';
import Warning from '~icons/line-md/alert-twotone-loop';
import Locked from '~icons/material-symbols/lock-outline';
import type { AppError } from '$api/types';
import { appErrorCodeSchema } from '$api/schemas';
import { get } from 'svelte/store';
import LL from '$i18n/i18n-svelte';

// Define the notification store
export const notificationStore = writable<
	{ id: number; message: string; Icon?: Component<SVGAttributes<SVGSVGElement>>; color: string }[]
>([]);

type NotificationType = 'success' | 'error' | 'warning' | 'info';
let nextId = 1;

export function notification(
	appError: AppError,
	config?: {
		Icon?: Component<SVGAttributes<SVGSVGElement>>;
		color?: string;
		duration?: number;
	}
): void;
export function notification(
	notificationType: NotificationType,
	message: string,
	config?: {
		Icon?: Component<SVGAttributes<SVGSVGElement>>;
		color?: string;
		duration?: number;
	}
): void;
export function notification(
	notificationTypeOrError: NotificationType | AppError,
	messageOrConfig?:
		| string
		| {
				Icon?: Component<SVGAttributes<SVGSVGElement>>;
				color?: string;
				duration?: number;
		  },
	config?: {
		Icon?: Component<SVGAttributes<SVGSVGElement>>;
		color?: string;
		duration?: number;
	}
) {
	const finalConfig = { duration: 5000, ...config };
	let notificationType: NotificationType;
	let message: string;

	if (appErrorCodeSchema.safeParse(notificationTypeOrError).success) {
		const appError = notificationTypeOrError as AppError;
		notificationType = 'error';
		const errorTranslations = get(LL).errors as Record<string, (() => string) | undefined>;
		message =
			errorTranslations[appError.error_code]?.() ||
			appError.detail ||
			get(LL).errors.unknown_error();

		if (typeof messageOrConfig === 'object') {
			Object.assign(finalConfig, messageOrConfig);
		}
	} else {
		notificationType = notificationTypeOrError as NotificationType;
		message = messageOrConfig as string;
	}

	const id = nextId++;

	if (!finalConfig.Icon) {
		if (notificationType === 'error') {
			finalConfig.Icon = Locked;
		} else if (notificationType === 'success') {
			finalConfig.Icon = Success;
		} else if (notificationType === 'warning') {
			finalConfig.Icon = Warning;
		} else {
			finalConfig.Icon = Error;
		}
	}

	finalConfig.color =
		finalConfig.color ||
		(notificationType === 'success' ? 'green' : notificationType === 'warning' ? 'orange' : 'red');

	notificationStore.update((notifications) => [
		...notifications,
		{ id, message, Icon: finalConfig.Icon, color: finalConfig.color! }
	]);
	const notificationFn = () => {
		notificationStore.update((notifications) =>
			notifications.filter((notification) => notification.id !== id)
		);
	};
	if (finalConfig.duration && finalConfig.duration > 0) {
		setTimeout(notificationFn, finalConfig.duration);
	} else {
		notificationFn();
	}
}
