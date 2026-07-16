import { Suspense } from "react";
import { AuthLoadingScreen } from "@/components/guards";
import { ForgotPasswordPageContent } from "./forgot-password-page-content";

export default function ForgotPasswordPage(): React.ReactElement {
  return (
    <Suspense fallback={<AuthLoadingScreen />}>
      <ForgotPasswordPageContent />
    </Suspense>
  );
}
