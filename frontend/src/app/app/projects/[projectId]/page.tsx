import Workspace from "@/components/workspace/Workspace";
export default async function Page({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  return <Workspace projectId={projectId} />;
}
