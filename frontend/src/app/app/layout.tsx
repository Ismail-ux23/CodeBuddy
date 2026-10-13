import AppShell from "@/components/shared/AppShell";
export const metadata = {
  robots: { index: false, follow: false },
  title: "Workspace · CodeBuddy",
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
