import { NextResponse, type NextRequest } from "next/server";

const PUBLIC_PATHS = ["/login", "/pricing", "/features", "/api", "/brand"];

function isPublic(pathname: string) {
  if (pathname === "/") return true;
  return PUBLIC_PATHS.some((path) => pathname === path || pathname.startsWith(`${path}/`));
}

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  if (isPublic(pathname)) return NextResponse.next();

  const required =
    process.env.NEXT_PUBLIC_AUTH_REQUIRED === "true" || process.env.AUTH_REQUIRED === "true";
  if (!required) return NextResponse.next();

  const token = request.cookies.get("ra_token")?.value;
  if (!token) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.search = `?next=${encodeURIComponent(`${pathname}${search}`)}`;
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
