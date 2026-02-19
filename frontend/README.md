# 🖥️ Frontend

> [Back to main README](../README.md)

SvelteKit application using Svelte 5, TypeScript (strict), and TailwindCSS 4. Handles SSR, client-side API calls, WebSocket connections, and the PDF annotation interface. Linting is handled by Prettier ([`.prettierrc`](.prettierrc)) and ESLint ([`eslint.config.js`](eslint.config.js)).

## 🛠️ Commands

All commands use `pnpm` and are run from `frontend/`.

| Task | Command |
|---|---|
| **Dev server** | `pnpm dev` |
| **Build** | `pnpm build` |
| **Type check** | `pnpm check` |
| **Lint** | `pnpm lint` |
| **Lint fix** | `pnpm lint:fix` |
| **Run all tests** | `pnpm test` |
| **Test with coverage** | `pnpm test:coverage` |
| **Regenerate types** | `pnpm typegen` |

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
  console.log(result.data);  // DocumentRead
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

---

## 📄 Generated Files

These files are auto-generated and **must not be edited manually**:

| File | Generator | Source |
|---|---|---|
| `src/api/types.ts` | `pydantic2ts` | Backend Pydantic models |
| `src/api/schemas.ts` | `ts-to-zod` | `types.ts` |
| `src/api/maps.generated.ts` | `generate_exclusion_maps.py` | Backend filter models |
| `src/i18n/i18n-types.ts` | `typesafe-i18n` | Translation files |

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
