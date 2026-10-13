import Link from "next/link";
export default function NotFound() {
  return (
    <main className="empty-state">
      <h1>Page not found.</h1>
      <p>This page may have moved, or you may not have access.</p>
      <Link className="button ghost" href="/">
        Back to CodeBuddy
      </Link>
    </main>
  );
}
