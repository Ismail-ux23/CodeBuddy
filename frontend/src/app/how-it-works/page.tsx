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
      <h1>From unfamiliar to understood.</h1>
      <section>
        <h2>01 · Bring your repository</h2>
        <p>
          Create a project and upload a ZIP. CodeBuddy checks paths and size
          limits, excludes unsupported and secret-bearing files, and prepares
          sanitized source for your review.
        </p>
      </section>
      <section>
        <h2>02 · Review, then index</h2>
        <p>
          Inspect the exclusion report and uncheck files you do not want
          included. With your confirmation, source excerpts go to Gemini for
          embeddings. CodeBuddy never runs uploaded code.
        </p>
      </section>
      <section>
        <h2>03 · Ask and inspect</h2>
        <p>
          Hybrid search combines exact identifiers, full-text search, and
          semantic retrieval. Answers distinguish source observations from
          inferences. Click a citation to open the exact snapshot and lines.
        </p>
      </section>
      <section>
        <h2>04 · Find your starting point</h2>
        <p>
          Generate an onboarding guide from repository evidence. Re-upload
          changes as a new snapshot; earlier conversations retain their original
          context.
        </p>
      </section>
      <Link className="button solid" href="/app/new">
        Analyze your code
      </Link>
    </main>
  );
}
