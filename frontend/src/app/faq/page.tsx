import Brand from "@/components/shared/Brand";
import Link from "next/link";
export default function Page() {
  return (
    <main className="info-page">
      <header>
        <Brand />
        <Link className="button ghost" href="/demo">
          Explore demo
        </Link>
      </header>
      <h1>A few good questions.</h1>
      <section>
        <h2>Does my code stay local?</h2>
        <p>
          Sanitized source is stored on your configured server. Once you approve
          indexing, excerpts are sent to Google Gemini for embeddings and
          generation. Review files before consenting; secret detection is
          best-effort.
        </p>
      </section>
      <section>
        <h2>Does CodeBuddy run my code?</h2>
        <p>
          No. CodeBuddy is read-only. It does not execute uploaded code, install
          dependencies, or follow instructions embedded in a repository.
        </p>
      </section>
      <section>
        <h2>Can I use it without a Gemini key?</h2>
        <p>
          Yes, for the bundled precomputed demo and sanitized source previews.
          Live indexing, answers, and guides require server-side Gemini
          configuration.
        </p>
      </section>
      <section>
        <h2>Are citations a guarantee of correctness?</h2>
        <p>
          No. Source IDs and line ranges are validated, and a separate model
          pass reviews support. You should inspect the evidence; model
          assessment is not proof.
        </p>
      </section>
      <section>
        <h2>What happens when I delete a project?</h2>
        <p>
          Its live source files and derived database records are removed. Any
          operator-managed backups remain subject to that operator’s retention
          policy.
        </p>
      </section>
      <section>
        <h2>Can I import from GitHub?</h2>
        <p>
          Not in this release. Upload a repository ZIP. GitHub integration,
          teams, billing, and architecture graphs are future work.
        </p>
      </section>
      <Link className="button solid" href="/app/new">
        Analyze your code
      </Link>
    </main>
  );
}
