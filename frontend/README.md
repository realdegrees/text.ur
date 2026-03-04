# 🖥️ Frontend

> [Back to main README](../README.md)

SvelteKit application using Svelte 5, TypeScript (strict), and TailwindCSS 4. Handles SSR, client-side API calls, WebSocket connections, and the PDF annotation interface. Linting is handled by Prettier ([`.prettierrc`](.prettierrc)) and ESLint ([`eslint.config.js`](eslint.config.js)).

## 🛠️ Commands

All commands use `pnpm` and are run from `frontend/`.

| Task                   | Command              |
| ---------------------- | -------------------- |
| **Dev server**         | `pnpm dev`           |
| **Build**              | `pnpm build`         |
| **Type check**         | `pnpm check`         |
| **Lint**               | `pnpm lint`          |
| **Lint fix**           | `pnpm lint:fix`      |
| **Run all tests**      | `pnpm test`          |
| **Test with coverage** | `pnpm test:coverage` |
| **Regenerate types**   | `pnpm typegen`       |

---

## 🧩 Key Patterns

### Hybrid Request Model

The app uses two backend base URLs:

- **`INTERNAL_BACKEND_BASEURL`** (private) - used by the SvelteKit server during SSR. The `handleFetch` hook in `hooks.server.ts` intercepts `/api/*` requests, rewrites them to this URL, and forwards cookies.
- **`PUBLIC_BACKEND_BASEURL`** (public) - used by the browser for client-side API calls and WebSocket connections.

See [Architecture: Request Flow](../docs/architecture.md#-request-flow) for details.

### API Client

The `ApiClient` singleton (`src/api/client.ts`) wraps `fetch` with automatic credentials, transparent 401/token refresh, and ETag caching. All methods return discriminated unions:

```typescript
const result = await api.get<DocumentRead>('/api/documents/abc');

if (result.success) {
	console.log(result.data); // DocumentRead
} else {
	console.log(result.error); // AppError
}
```

### Server Hooks

`hooks.server.ts` handles SSR API proxying (rewrites to `INTERNAL_BACKEND_BASEURL`), cookie forwarding, transparent token refresh during SSR, security headers, dark mode detection, and i18n locale detection.

### WebSocket

`documentWebSocket.svelte.ts` manages the real-time connection for the document viewer. WebSocket connections go directly from the browser to the backend via `PUBLIC_BACKEND_BASEURL`. The store handles comment sync (create/update/delete), active user tracking with heartbeat, live cursor positions, and automatic reconnection with exponential backoff.

### PDF Rendering

The PDF viewer uses [PDFSlick](https://pdfslick.dev/) (`@pdfslick/core`). Key components live in `lib/components/pdf/`:

- `Pdf.svelte` - core renderer
- `AnnotationLayer.svelte` - overlay for annotation bounding boxes
- `TextSelectionHandler.svelte` - text selection for creating annotations
- `ConnectionLines.svelte` - visual lines connecting annotations to comments
- `CommentSidebar.svelte` - scrollable comment panel

#### Text Selection Handles

When users select text to create an annotation, adjustable selection handles (teardrops) let them refine the selection range. The implementation uses a hybrid approach because no browser API can detect whether native OS selection handles are available:

**Detection strategy** (`lib/util/responsive.svelte.ts` → `pointerState`):

1. **Reactive pointer-type tracking** — a global `pointerdown` listener records `e.pointerType` (`'mouse'`, `'touch'`, or `'pen'`) in reactive `$state`. This updates dynamically as the user switches input methods on hybrid devices.
2. **Platform heuristics** — user-agent detection identifies iOS and Android as platforms with reliable native selection handles. All other platforms (Windows, ChromeOS, etc.) are treated as unreliable.
3. **Combined decision** — `pointerState.showCustomHandles` returns `true` when using mouse/pen (native handles never exist), or when using touch on a platform without reliable native handles.

**Behavior by device:**

| Input       | Platform                   | Custom handles | Native handles       |
| ----------- | -------------------------- | -------------- | -------------------- |
| Mouse / pen | Any                        | Shown          | Not present          |
| Touch       | iOS / Android              | Hidden         | Present (reliable)   |
| Touch       | Windows / ChromeOS / other | Shown          | May or may not exist |

**Known limitation:** On Windows touch devices where the browser _does_ provide native selection handles, both native and custom handles may appear simultaneously. This is cosmetic — both remain functional. A fully custom touch selection system (bypassing native `Selection` API entirely) would eliminate this overlap but would require significantly more work. See the [Known Issues](../README.md#text-selection-handles-on-hybrid-touch-devices) section for user-facing context.

**Key files:**

- `lib/util/responsive.svelte.ts` — `pointerState` singleton (pointer tracking + platform detection)
- `lib/components/pdf/TextSelectionHandler.svelte` — handle rendering, drag logic, `selectionchange` sync
- `lib/actions/preciseHover.ts` — retains the older `hasHoverCapability()` check (hover-specific, not handle-related)

---

## 📄 Generated Files

These files are auto-generated and **must not be edited manually**:

| File                        | Generator                    | Source                  |
| --------------------------- | ---------------------------- | ----------------------- |
| `src/api/types.ts`          | `pydantic2ts`                | Backend Pydantic models |
| `src/api/schemas.ts`        | `ts-to-zod`                  | `types.ts`              |
| `src/api/maps.generated.ts` | `generate_exclusion_maps.py` | Backend filter models   |
| `src/i18n/i18n-types.ts`    | `typesafe-i18n`              | Translation files       |

After any backend model change:

```bash
pnpm typegen
```

Always commit the regenerated files alongside model changes. The CI pipeline fails if they are out of sync.

---

## 🌐 Internationalization

The project uses [typesafe-i18n](https://github.com/ivanhofer/typesafe-i18n) with English (`en`) and German (`de`). Add translation keys in `src/i18n/en/index.ts`, then add the corresponding German translations in `src/i18n/de/index.ts`. Types are generated automatically.

---

## 🧪 Testing

Tests use `.spec.ts` files and vitest (`describe`/`it`/`expect`).
