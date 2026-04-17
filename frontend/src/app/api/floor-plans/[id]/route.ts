import { getServerSession } from "next-auth";
import { NextResponse } from "next/server";

import { authOptions } from "@/lib/auth";
import { deleteFloorPlan, updateFloorPlanDetails } from "@/lib/floorPlans";

export const runtime = "nodejs";

type FloorPlanRouteContext = {
  params: Promise<{
    id: string;
  }>;
};

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
        : "Could not update this floor plan.",
    status: possibleError.code === "not-owner" ? 403 : 400,
  };
}

export async function PATCH(request: Request, { params }: FloorPlanRouteContext) {
  const session = await getServerSession(authOptions);

  if (!session?.user?.email) {
    return NextResponse.json({ error: "Login required." }, { status: 401 });
  }

  const body = (await request.json().catch(() => null)) as {
    title?: unknown;
    description?: unknown;
  } | null;
  const title = typeof body?.title === "string" ? body.title : "";
  const description = typeof body?.description === "string" ? body.description : "";
  const { id } = await params;

  try {
    const floorPlan = await updateFloorPlanDetails(id, {
      title,
      description,
      userEmail: session.user.email,
    });

    if (!floorPlan) {
      return NextResponse.json({ error: "Floor plan not found." }, { status: 404 });
    }

    return NextResponse.json({ floorPlan });
  } catch (error) {
    const interactionError = getInteractionErrorStatus(error);

    if (interactionError) {
      return NextResponse.json(
        { error: interactionError.message },
        { status: interactionError.status },
      );
    }

    console.error("Could not update floor plan", error);
    return NextResponse.json({ error: "Could not update this floor plan." }, { status: 500 });
  }
}

export async function DELETE(_request: Request, { params }: FloorPlanRouteContext) {
  const session = await getServerSession(authOptions);

  if (!session?.user?.email) {
    return NextResponse.json({ error: "Login required." }, { status: 401 });
  }

  const { id } = await params;

  try {
    const deleted = await deleteFloorPlan(id, session.user.email);

    if (!deleted) {
      return NextResponse.json({ error: "Floor plan not found." }, { status: 404 });
    }

    return NextResponse.json({ deleted: true });
  } catch (error) {
    const interactionError = getInteractionErrorStatus(error);

    if (interactionError) {
      return NextResponse.json(
        { error: interactionError.message },
        { status: interactionError.status },
      );
    }

    console.error("Could not delete floor plan", error);
    return NextResponse.json({ error: "Could not delete this floor plan." }, { status: 500 });
  }
}
