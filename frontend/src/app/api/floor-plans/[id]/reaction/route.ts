import { getServerSession } from "next-auth";
import { NextResponse } from "next/server";

import { authOptions } from "@/lib/auth";
import { setFloorPlanReaction, type FloorPlanReactionType } from "@/lib/floorPlans";

export const runtime = "nodejs";

type ReactionRouteContext = {
  params: Promise<{
    id: string;
  }>;
};

function parseReaction(value: unknown): FloorPlanReactionType | null | undefined {
  if (value === "like" || value === "dislike") {
    return value;
  }

  if (value === null || value === "none") {
    return null;
  }

  return undefined;
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
    message: typeof possibleError.message === "string" ? possibleError.message : "Could not save reaction.",
    status: possibleError.code === "own-plan" ? 403 : 400,
  };
}

export async function POST(request: Request, { params }: ReactionRouteContext) {
  const session = await getServerSession(authOptions);

  if (!session?.user?.email) {
    return NextResponse.json({ error: "Login required." }, { status: 401 });
  }

  const body = (await request.json().catch(() => null)) as { reaction?: unknown } | null;
  const reaction = parseReaction(body?.reaction);

  if (reaction === undefined) {
    return NextResponse.json({ error: "Choose like, dislike, or none." }, { status: 400 });
  }

  const { id } = await params;

  try {
    const floorPlan = await setFloorPlanReaction(
      id,
      {
        email: session.user.email,
        name: session.user.name ?? session.user.email,
      },
      reaction,
    );

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

    console.error("Could not save floor plan reaction", error);
    return NextResponse.json({ error: "Could not save reaction." }, { status: 500 });
  }
}
