import { Suspense } from "react";
import { AuthLoadingScreen } from "@/components/guards";
import { RegisterPageContent } from "./register-page-content";

export default function RegisterPage(): React.ReactElement {
  return (
    <Suspense fallback={<AuthLoadingScreen />}>
      <RegisterPageContent />
    </Suspense>
  );
}
