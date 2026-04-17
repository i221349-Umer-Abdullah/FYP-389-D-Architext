import type { Metadata } from "next";
import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";
import { Suspense } from "react";

import { SiteHeader } from "@/components/layout/SiteHeader";
import { StudioShell } from "@/components/studio/StudioShell";
import { authOptions } from "@/lib/auth";

export const metadata: Metadata = {
  title: "Studio | Architext",
  description: "Interactive frontend studio for 3D floor plan analysis.",
};

type StudioPageProps = {
  searchParams?: Promise<{
    prompt?: string | string[];
  }>;
};

export default async function StudioPage({ searchParams }: StudioPageProps) {
  const session = await getServerSession(authOptions);

  if (!session) {
    const resolvedSearchParams = await searchParams;
    const promptParam = resolvedSearchParams?.prompt;
    const prompt = Array.isArray(promptParam) ? promptParam[0] : promptParam;
    const callbackUrl = prompt ? `/studio?prompt=${encodeURIComponent(prompt)}` : "/studio";

    redirect(`/auth?callbackUrl=${encodeURIComponent(callbackUrl)}`);
  }

  return (
    <>
      <SiteHeader />
      <main>
        <Suspense fallback={<div className="app-container">Loading studio...</div>}>
          <StudioShell />
        </Suspense>
      </main>
    </>
  );
}
