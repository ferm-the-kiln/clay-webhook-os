import { NextRequest, NextResponse } from "next/server";

const COOKIE_NAME = "clay-dash-auth";
const COOKIE_MAX_AGE = 60 * 60 * 24 * 30; // 30 days

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}));
  const password = body.password as string | undefined;
  const secret = process.env.DASHBOARD_SECRET;

  if (!secret) {
    return NextResponse.json(
      { error: "DASHBOARD_SECRET not configured" },
      { status: 500 }
    );
  }

  if (!password || password !== secret) {
    return NextResponse.json(
      { error: "Invalid password" },
      { status: 401 }
    );
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.set(COOKIE_NAME, secret, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: COOKIE_MAX_AGE,
    path: "/",
  });

  return response;
}

export async function DELETE() {
  const response = NextResponse.json({ ok: true });
  response.cookies.delete(COOKIE_NAME);
  return response;
}
