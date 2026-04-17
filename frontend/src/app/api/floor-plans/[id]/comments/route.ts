import { getServerSession } from "next-auth";
import { NextResponse } from "next/server";

import { authOptions } from "@/lib/auth";
import { addFloorPlanComment, addFloorPlanReply } from "@/lib/floorPlans";

export const runtime = "nodejs";

type CommentsRouteContext = {
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
    message: typeof possibleError.message === "string" ? possibleError.message : "Could not save comment.",
    status: possibleError.code === "own-plan" ? 403 : possibleError.code === "missing-comment" ? 404 : 400,
  };
}

export async function POST(request: Request, { params }: CommentsRouteContext) {
  const session = await getServerSession(authOptions);

  if (!session?.user?.email) {
    return NextResponse.json({ error: "Login required." }, { status: 401 });
  }

  const body = (await request.json().catch(() => null)) as {
    body?: unknown;
    parentCommentId?: unknown;
  } | null;
  const commentBody = typeof body?.body === "string" ? body.body : "";
  const parentCommentId = typeof body?.parentCommentId === "string" ? body.parentCommentId : "";

  const { id } = await params;

  try {
    const user = {
      email: session.user.email,
      name: session.user.name ?? session.user.email,
    };
    const floorPlan = parentCommentId
      ? await addFloorPlanReply(id, user, parentCommentId, commentBody)
      : await addFloorPlanComment(id, user, commentBody);

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

    console.error("Could not save floor plan comment", error);
    return NextResponse.json({ error: "Could not save comment." }, { status: 500 });
  }
}
