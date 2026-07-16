import { NextResponse, type NextRequest } from "next/server";

const protectedPaths = ["/dashboard", "/settings", "/team"];

export function middleware(request: NextRequest): NextResponse {
  if (
    protectedPaths.some((path) => request.nextUrl.pathname.startsWith(path)) &&
    !request.cookies.get("auth_session")
  ) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/settings/:path*", "/team/:path*"],
};
