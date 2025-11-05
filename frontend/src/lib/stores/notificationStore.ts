import type { Component } from 'svelte';
import type { SVGAttributes } from 'svelte/elements';
import { writable } from 'svelte/store';
import Success from '~icons/line-md/confirm-square-twotone';
import Error from '~icons/line-md/alert-square-twotone-loop';
import Warning from '~icons/line-md/alert-twotone-loop';
import Locked from '~icons/material-symbols/lock-outline';

// Define the notification store
export const notificationStore = writable<
	{ id: number; message: string; Icon?: Component<SVGAttributes<SVGSVGElement>>; color: string }[]
>([]);

type NotificationType = 'success' | 'error' | 'warning' | 'info';

let nextId = 1;

/**
 * Function to trigger a notification
 * @param code - The status code of the notification
 * @param message - The message to display
 * @param Icon - The icon component to display
 * @param color - The color of the notification (tailwind class)
 * @param duration - The duration to display the notification (in milliseconds). If undefined or 0, the notification will not auto-dismiss.
 */
export function notification(
	notificationType: NotificationType,
	message: string,
	config: {
		Icon?: Component<SVGAttributes<SVGSVGElement>>,
		color?: string,
		duration: number | undefined
	} = { duration: 5000 }
) {
	const id = nextId++;

	if (!config.Icon) {
		if (notificationType === 'error') {
			config.Icon = Locked;
		} else if (notificationType === 'success') {
			config.Icon = Success;
		} else if (notificationType === 'warning') {
			config.Icon = Warning;
		} else {
			config.Icon = Error;
		}
	}

	config.color =
		config.color ||
		(notificationType === 'success'
			? 'green'
			: notificationType === 'warning'
				? 'orange'
				: 'red');

	notificationStore.update((notifications) => [...notifications, { id, message, Icon: config.Icon, color: config.color! }]);
	const notificationFn = () => {
		notificationStore.update((notifications) =>
			notifications.filter((notification) => notification.id !== id)
		);
	};
	if (config.duration && config.duration > 0) {
		setTimeout(notificationFn, config.duration);
	} else {
		notificationFn();
	}
}
