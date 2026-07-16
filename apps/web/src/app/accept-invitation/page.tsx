import { AcceptInvitationPageContent } from "./accept-invitation-page-content";

export default async function AcceptInvitationPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>;
}): Promise<React.ReactElement> {
  const { token } = await searchParams;
  return <AcceptInvitationPageContent token={token ?? null} />;
}
