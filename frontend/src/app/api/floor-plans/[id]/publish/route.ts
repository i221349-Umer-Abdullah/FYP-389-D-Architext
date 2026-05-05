import { getServerSession } from "next-auth";
import { NextResponse } from "next/server";

import { authOptions } from "@/lib/auth";
import { setFloorPlanPublic } from "@/lib/floorPlans";

export const runtime = "nodejs";

type RouteContext = { params: Promise<{ id: string }> };

function getInteractionErrorStatus(error: unknown) {
  if (typeof error !== "object" || error === null) return null;
  const e = error as { code?: unknown; message?: unknown; name?: unknown };
  if (e.name !== "FloorPlanInteractionError") return null;
  return {
    message: typeof e.message === "string" ? e.message : "Could not update this floor plan.",
    status: e.code === "not-owner" ? 403 : 400,
  };
}

export async function POST(request: Request, { params }: RouteContext) {
  const session = await getServerSession(authOptions);

  if (!session?.user?.email) {
    return NextResponse.json({ error: "Login required." }, { status: 401 });
  }

  const body = (await request.json().catch(() => null)) as { isPublic?: unknown } | null;
  if (typeof body?.isPublic !== "boolean") {
    return NextResponse.json({ error: "isPublic (boolean) is required." }, { status: 400 });
  }

  const { id } = await params;

  try {
    const plan = await setFloorPlanPublic(id, session.user.email, body.isPublic);
    if (!plan) return NextResponse.json({ error: "Floor plan not found." }, { status: 404 });
    return NextResponse.json({ floorPlan: plan });
  } catch (error) {
    const ie = getInteractionErrorStatus(error);
    if (ie) return NextResponse.json({ error: ie.message }, { status: ie.status });
    console.error("Could not update floor plan visibility", error);
    return NextResponse.json({ error: "Could not update floor plan visibility." }, { status: 500 });
  }
}
