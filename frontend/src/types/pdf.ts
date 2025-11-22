/**
 * Represents a PDF annotation with text selection and bounding boxes
 */
export interface Annotation {
	text: string;
	boundingBoxes: BoundingBox[];
	color: string;
}

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