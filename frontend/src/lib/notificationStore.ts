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
	code: number,
	message: string,
	Icon?: Component<SVGAttributes<SVGSVGElement>>,
	color?: string,
	duration: number | undefined = 5000
) {
	const id = nextId++;

	if (!Icon) {
		if (code === 403 || code === 401) {
			Icon = Locked;
		} else if (code.toString().startsWith('2')) {
			Icon = Success;
		} else if (code.toString().startsWith('4')) {
			Icon = Warning;
		} else {
			Icon = Error;
		}
	}

	color =
		color ||
		(code.toString().startsWith('2')
			? 'green'
			: code.toString().startsWith('4')
				? 'orange'
				: 'red');

	notificationStore.update((notifications) => [...notifications, { id, message, Icon, color }]);
	const notificationFn = () => {
		notificationStore.update((notifications) =>
			notifications.filter((notification) => notification.id !== id)
		);
	};
	if (duration && duration > 0) {
		setTimeout(notificationFn, duration);
	} else {
		notificationFn();
	}
}
