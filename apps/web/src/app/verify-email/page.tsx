import { VerifyEmailPageContent } from "./verify-email-page-content";

export default async function VerifyEmailPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>;
}): Promise<React.ReactElement> {
  const { token } = await searchParams;
  return <VerifyEmailPageContent token={token ?? null} />;
}
