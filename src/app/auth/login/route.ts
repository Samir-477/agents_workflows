import { NextResponse } from "next/server";
import { COOKIE_NAME, createSession } from "@/lib/session";

function credentials() {
  const email=process.env.STELLAR_ADMIN_EMAIL;
  const password=process.env.STELLAR_ADMIN_PASSWORD;
  if (email&&password) return {email,password};
  if (process.env.NODE_ENV!=="production") return {email:"admin@gmail.com",password:"admin123"};
  return null;
}

export async function POST(request: Request) {
  const payload = (await request.json().catch(() => null)) as
    | { email?: string; password?: string }
    | null;

  const expected=credentials();
  if (!expected) return NextResponse.json({error:"Production authentication is not configured."},{status:503});
  if (payload?.email !== expected.email || payload.password !== expected.password) {
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
