import type { Component } from 'svelte';

export interface TutorialMedia {
	src: string;
	alt: string;
}

export interface TutorialStep {
	title: string;
	description?: string;
	component?: Component;
	componentProps?: Record<string, any>;
	media: TutorialMedia;
}
