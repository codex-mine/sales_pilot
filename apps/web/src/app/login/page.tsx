import { Suspense } from "react";
import { AuthLoadingScreen } from "@/components/guards";
import { LoginPageContent } from "./login-page-content";

export default function LoginPage(): React.ReactElement {
  return (
    <Suspense fallback={<AuthLoadingScreen />}>
      <LoginPageContent />
    </Suspense>
  );
}
