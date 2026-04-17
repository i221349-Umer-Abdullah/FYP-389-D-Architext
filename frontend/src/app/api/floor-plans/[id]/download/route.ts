import { getServerSession } from "next-auth";
import { NextResponse } from "next/server";

import { authOptions } from "@/lib/auth";
import { openFloorPlanDownload } from "@/lib/floorPlans";

export const runtime = "nodejs";

type DownloadRouteContext = {
  params: Promise<{
    id: string;
  }>;
};

function contentDispositionFileName(fileName: string) {
  return fileName.replace(/["\\]/g, "");
}

export async function GET(_request: Request, { params }: DownloadRouteContext) {
  const session = await getServerSession(authOptions);

  if (!session?.user) {
    return NextResponse.json({ error: "Login required." }, { status: 401 });
  }

  const { id } = await params;
  const download = await openFloorPlanDownload(id);

  if (!download) {
    return NextResponse.json({ error: "Floor plan not found." }, { status: 404 });
  }

  return new Response(download.stream, {
    headers: {
      "Content-Type": download.version.mimeType,
      "Content-Length": String(download.version.size),
      "Content-Disposition": `attachment; filename="${contentDispositionFileName(download.version.originalName)}"`,
    },
  });
}
