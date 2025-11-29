import z from 'zod';

/**
 * Represents a bounding box for text selection in normalized coordinates relative to the page (0-1)
 */
export interface BoundingBox {
	pageNumber: number;
	x: number;
	y: number;
	width: number;
	height: number;
}

/**
 * Represents a PDF annotation with text selection and bounding boxes
 */
export interface Annotation {
	text: string;
	boundingBoxes: BoundingBox[];
	color: string;
}

const boundingBoxSchema = z.object({
	pageNumber: z.number(),
	x: z.number(),
	y: z.number(),
	width: z.number(),
	height: z.number()
});

export const annotationSchema = z.object({
	text: z.string(),
	boundingBoxes: z.array(boundingBoxSchema).min(1),
	color: z.string().default('rgba(255, 235, 59, 0.4)')
});
