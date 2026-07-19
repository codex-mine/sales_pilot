import { BookingPageContent } from "./booking-page-content";

export default async function BookingPage({
  params,
}: {
  params: Promise<{ token: string }>;
}): Promise<React.ReactElement> {
  const { token } = await params;

  return <BookingPageContent bookingToken={token} />;
}
