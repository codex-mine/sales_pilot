# Architecture

Phase 1 establishes an explicit seam for future capabilities: feature modules own their APIs, services coordinate use cases, repositories isolate persistence, and workers are reserved for asynchronous work. The initial authorization model uses memberships (`owner`, `admin`, `member`) scoped to organizations. Future AI and campaign modules must not bypass this tenant boundary.

The web application uses App Router, TanStack Query for server state, Zustand only for small client state, and a shared Axios client. Secure cookies are preferred for refresh credentials; the access token is short lived and should remain memory-only when the login UI is connected.
