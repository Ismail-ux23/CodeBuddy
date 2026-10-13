import Upload from "@/components/workspace/Upload";
export default function Page() {
  return (
    <main className="narrow-page">
      <p className="eyebrow">NEW PROJECT</p>
      <h1>Bring your code.</h1>
      <p className="muted">
        Turn an unfamiliar repository into a place you know.
      </p>
      <Upload />
    </main>
  );
}
