import { getServerSession } from "next-auth";
import { NextResponse } from "next/server";

import { authOptions } from "@/lib/auth";
import {
  addFloorPlanVersion,
  isAllowedFloorPlanFile,
  MAX_FLOOR_PLAN_UPLOAD_BYTES,
} from "@/lib/floorPlans";

export const runtime = "nodejs";

type VersionsRouteContext = {
  params: Promise<{
    id: string;
  }>;
};

function isUploadedFile(value: FormDataEntryValue | null): value is File {
  return (
    typeof value === "object" &&
    value !== null &&
    "name" in value &&
    "size" in value &&
    "type" in value &&
    "arrayBuffer" in value &&
    typeof value.name === "string" &&
    typeof value.size === "number" &&
    typeof value.type === "string" &&
    typeof value.arrayBuffer === "function"
  );
}

function getInteractionErrorStatus(error: unknown) {
  if (typeof error !== "object" || error === null) {
    return null;
  }

  const possibleError = error as { code?: unknown; message?: unknown; name?: unknown };

  if (possibleError.name !== "FloorPlanInteractionError") {
    return null;
  }

  return {
    message:
      typeof possibleError.message === "string"
        ? possibleError.message
        : "Could not save this new version.",
    status: possibleError.code === "not-owner" ? 403 : 400,
  };
}

export async function POST(request: Request, { params }: VersionsRouteContext) {
  const session = await getServerSession(authOptions);

  if (!session?.user?.email) {
    return NextResponse.json({ error: "Login required." }, { status: 401 });
  }

  try {
    const formData = await request.formData();
    const file = formData.get("file");

    if (!isUploadedFile(file)) {
      return NextResponse.json({ error: "Choose a revised floor plan file." }, { status: 400 });
    }

    if (!isAllowedFloorPlanFile(file.name)) {
      return NextResponse.json(
        { error: "Upload a PDF, image, IFC, JSON, DWG, DXF, or ZIP file." },
        { status: 400 },
      );
    }

    if (file.size <= 0) {
      return NextResponse.json({ error: "The selected file is empty." }, { status: 400 });
    }

    if (file.size > MAX_FLOOR_PLAN_UPLOAD_BYTES) {
      return NextResponse.json({ error: "File must be 25 MB or smaller." }, { status: 400 });
    }

    const { id } = await params;
    const floorPlan = await addFloorPlanVersion(id, {
      originalName: file.name,
      mimeType: file.type,
      size: file.size,
      contents: Buffer.from(await file.arrayBuffer()),
      uploaderName: session.user.name ?? session.user.email,
      uploaderEmail: session.user.email,
    });

    if (!floorPlan) {
      return NextResponse.json({ error: "Floor plan not found." }, { status: 404 });
    }

    return NextResponse.json({ floorPlan }, { status: 201 });
  } catch (error) {
    const interactionError = getInteractionErrorStatus(error);

    if (interactionError) {
      return NextResponse.json(
        { error: interactionError.message },
        { status: interactionError.status },
      );
    }

    console.error("Could not save floor plan version", error);
    return NextResponse.json({ error: "Could not save this new version." }, { status: 500 });
  }
}
