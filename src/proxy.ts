import { type NextRequest, NextResponse } from "next/server";

export function proxy(request: NextRequest) {
  const path = request.nextUrl.pathname;
  const authenticated =
    request.cookies.get("stellar_demo_session")?.value === "stellar-admin";

  if (path.startsWith("/agents") && !authenticated) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  if ((path === "/" || path === "/login") && authenticated) {
    return NextResponse.redirect(new URL("/agents", request.url));
  }
  if (path === "/") {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/", "/login", "/agents/:path*"],
};
