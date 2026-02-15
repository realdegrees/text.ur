// PDF viewer constants
export const PDF_ZOOM_STEP = 0.2;
export const PDF_MIN_SCALE = 0.5;

// Annotation constants
export const DEFAULT_HIGHLIGHT_COLOR = '#916D5E';

// Box merging constants for text selection
export const BOX_MERGE_MARGIN = 0.005; // Normalized coordinates (0-1)
export const BOX_VERTICAL_OVERLAP_THRESHOLD = 0.5; // 50% of smaller box height

// Comment sidebar constants
export const CLUSTER_THRESHOLD_PX = 60;
export const BADGE_HEIGHT_PX = 32;

// Animation/timing constants
export const OPACITY_TRANSITION_MS = 100;
export const INITIAL_RENDER_DELAY_MS = 200;

// Connection line constants
export const LINE_CORNER_RADIUS = 6; // px radius for rounded corners on bends
export const LINE_CHANNEL_GAP = 8; // px gap between PDF right edge and vertical channel
export const LINE_STROKE_WIDTH = 1.5; // px stroke width for non-hovered lines
export const LINE_HOVERED_STROKE_WIDTH = 3; // px stroke width for hovered/active line
export const LINE_ENDPOINT_RADIUS = 3; // px radius for endpoint dots
export const LINE_FADE_MS = 150; // ms for fade in/out transitions
export const LINE_OPACITY = 0.6; // opacity for all connection lines
