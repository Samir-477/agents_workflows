import { NextResponse } from "next/server";
import { COOKIE_NAME, createSession } from "@/lib/session";

const DEMO_EMAIL = "demo@stellar.ai";
const DEMO_PASSWORD = "stellar123";

export async function POST(request: Request) {
  const payload = (await request.json().catch(() => null)) as
    | { email?: string; password?: string }
    | null;

  if (payload?.email !== DEMO_EMAIL || payload.password !== DEMO_PASSWORD) {
    return NextResponse.json(
      { error: "Incorrect email or password." },
      { status: 401 },
    );
  }

  const response = NextResponse.json({ authenticated: true });
  response.cookies.set(COOKIE_NAME, await createSession("admin"), {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "strict",
    maxAge: 60 * 60 * 8,
    path: "/",
  });
  return response;
}
