import { NextResponse, type NextRequest } from "next/server";

/**
 * Edge-level gate. This is a fast, coarse first line of defense — it only
 * checks for the *presence* of the `access_token` cookie (the same cookie
 * name the backend sets in `app/auth/cookies.py`; it's httpOnly, which
 * blocks `document.cookie` in the browser but does not block the server
 * reading it here). It does not decode the JWT or check roles/permissions —
 * that's what `<AuthGuard>`/`<RoleGuard>`/`<PermissionGuard>` do client-side,
 * where the actual user/permission data from `/auth/me` is available.
 *
 * A stale/expired-but-present cookie will still pass this check and get
 * caught by `<AuthGuard>` once the client-side `initialize()` call runs (and
 * the API client's 401 interceptor will have already tried a refresh before
 * giving up) — this middleware only prevents the flash of protected content
 * for visitors with *no* session at all.
 */
const ACCESS_TOKEN_COOKIE = "access_token";

const protectedPaths = ["/dashboard", "/settings", "/organization", "/campaigns", "/ai", "/team"];
const guestOnlyPaths = ["/login", "/register", "/forgot-password"];

export function middleware(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;
  const hasSession = Boolean(request.cookies.get(ACCESS_TOKEN_COOKIE));

  if (protectedPaths.some((path) => pathname.startsWith(path)) && !hasSession) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  if (guestOnlyPaths.some((path) => pathname.startsWith(path)) && hasSession) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/settings/:path*",
    "/organization/:path*",
    "/campaigns/:path*",
    "/ai/:path*",
    "/team/:path*",
    "/login",
    "/register",
    "/forgot-password",
  ],
};
