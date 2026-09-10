import { type NextRequest, NextResponse } from "next/server";
import { COOKIE_NAME, verifySession } from "@/lib/session";

export async function proxy(request: NextRequest) {
  const path = request.nextUrl.pathname;
  const authenticated = await verifySession(request.cookies.get(COOKIE_NAME)?.value);

  if ((path.startsWith("/agents") || path.startsWith("/diagnosis")) && !authenticated) {
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
  matcher: ["/", "/login", "/agents/:path*", "/diagnosis/:path*"],
};
