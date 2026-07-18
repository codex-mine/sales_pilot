import { UnsubscribePageContent } from "./unsubscribe-page-content";

export default async function UnsubscribePage({
  params,
}: {
  params: Promise<{ token: string }>;
}): Promise<React.ReactElement> {
  const { token } = await params;

  return <UnsubscribePageContent token={token} />;
}
