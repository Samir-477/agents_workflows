import { NextResponse } from "next/server";

const DEMO_EMAIL = "admin@gmail.com";
const DEMO_PASSWORD = "admin123";

export async function POST(request: Request) {
  const payload = (await request.json().catch(() => null)) as
    | { email?: string; password?: string }
    | null;

  if (payload?.email !== DEMO_EMAIL || payload.password !== DEMO_PASSWORD) {
    return NextResponse.json(
      { error: "Incorrect demo email or password." },
      { status: 401 },
    );
  }

  const response = NextResponse.json({ authenticated: true });
  response.cookies.set("stellar_demo_session", "stellar-admin", {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 60 * 60 * 8,
    path: "/",
  });
  return response;
}
