import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-clay-900 text-clay-100">
      <h1 className="text-6xl font-bold text-clay-300 mb-2">404</h1>
      <p className="text-lg text-clay-400 mb-6">Page not found</p>
      <Link
        href="/"
        className="px-4 py-2 rounded-lg bg-kiln-teal text-clay-950 font-semibold hover:bg-kiln-teal-light transition-colors"
      >
        Back to Functions
      </Link>
    </div>
  );
}
