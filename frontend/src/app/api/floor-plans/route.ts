import { getServerSession } from "next-auth";
import { NextResponse } from "next/server";

import { authOptions } from "@/lib/auth";
import {
  createFloorPlan,
  getFloorPlan,
  isAllowedFloorPlanFile,
  MAX_FLOOR_PLAN_UPLOAD_BYTES,
  readFloorPlans,
  readUserFloorPlans,
} from "@/lib/floorPlans";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

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

export async function GET(request: Request) {
  const session = await getServerSession(authOptions);

  if (!session?.user?.email) {
    return NextResponse.json({ error: "Login required." }, { status: 401 });
  }

  const url = new URL(request.url);
  const floorPlans =
    url.searchParams.get("mine") === "1"
      ? await readUserFloorPlans(session.user.email)
      : await readFloorPlans(session.user.email);

  return NextResponse.json({ floorPlans });
}

export async function POST(request: Request) {
  try {
    const session = await getServerSession(authOptions);

    if (!session?.user?.email) {
      return NextResponse.json({ error: "Login required." }, { status: 401 });
    }

    const formData = await request.formData();
    const title = String(formData.get("title") ?? "");
    const description = String(formData.get("description") ?? "");
    const studioDataRaw = formData.get("studioData");
    const studioData = studioDataRaw ? String(studioDataRaw) : undefined;
    const file = formData.get("file");

    if (!isUploadedFile(file)) {
      return NextResponse.json({ error: "Choose a floor plan file." }, { status: 400 });
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

    const isPublicRaw = formData.get("isPublic");
    const isPublic = isPublicRaw === "true" || isPublicRaw === "1";

    const record = await createFloorPlan({
      title,
      description,
      originalName: file.name,
      mimeType: file.type,
      size: file.size,
      contents: Buffer.from(await file.arrayBuffer()),
      uploaderName: session.user.name ?? session.user.email,
      uploaderEmail: session.user.email,
      isPublic,
      studioData,
    });

    const savedRecord = await getFloorPlan(record.id, session.user.email);

    if (!savedRecord) {
      return NextResponse.json(
        { error: "Upload finished, but the floor plan was not saved in MongoDB." },
        { status: 500 },
      );
    }

    return NextResponse.json({ floorPlan: savedRecord }, { status: 201 });
  } catch (error) {
    console.error("Could not save uploaded floor plan", error);
    return NextResponse.json(
      { error: "Could not save this floor plan in MongoDB. Try again with a smaller file." },
      { status: 500 },
    );
  }
}
