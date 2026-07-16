import { ResetPasswordPageContent } from "./reset-password-page-content";

export default async function ResetPasswordPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>;
}): Promise<React.ReactElement> {
  const { token } = await searchParams;
  return <ResetPasswordPageContent token={token ?? null} />;
}
