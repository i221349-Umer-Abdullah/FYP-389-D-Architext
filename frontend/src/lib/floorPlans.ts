import path from "path";
import { Readable } from "stream";
import { finished } from "stream/promises";
import mongoose from "mongoose";
import { GridFSBucket, ObjectId } from "mongodb";

import { connectDB } from "@/lib/db";
import type { FloorPlanReactionType } from "@/lib/models/FloorPlan";

export type { FloorPlanReactionType } from "@/lib/models/FloorPlan";

export type FloorPlanCommentRecord = {
  id: string;
  body: string;
  userName: string;
  userEmail: string;
  createdAt: string;
  replies: FloorPlanCommentReplyRecord[];
};

export type FloorPlanCommentReplyRecord = {
  id: string;
  body: string;
  userName: string;
  userEmail: string;
  createdAt: string;
};

export type FloorPlanVersionRecord = {
  id: string;
  versionNumber: number;
  originalName: string;
  fileId: string;
  mimeType: string;
  size: number;
  uploadedAt: string;
  uploaderName: string;
  uploaderEmail: string;
  isLatest: boolean;
};

export type FloorPlanRecord = {
  id: string;
  title: string;
  description: string;
  originalName: string;
  fileId: string;
  mimeType: string;
  size: number;
  uploaderName: string;
  uploaderEmail: string;
  uploadedAt: string;
  isPublic: boolean;
  studioData?: string;
  likeCount: number;
  dislikeCount: number;
  userReaction: FloorPlanReactionType | null;
  commentCount: number;
  comments: FloorPlanCommentRecord[];
  canInteract: boolean;
  canUploadVersion: boolean;
  latestVersionNumber: number;
  versions: FloorPlanVersionRecord[];
};

export type FloorPlanDownload = {
  record: FloorPlanRecord;
  version: FloorPlanVersionRecord;
  stream: ReadableStream<Uint8Array>;
};

type CreateFloorPlanInput = {
  title: string;
  description: string;
  originalName: string;
  mimeType: string;
  size: number;
  contents: Buffer;
  uploaderName: string;
  uploaderEmail: string;
  isPublic?: boolean;
  studioData?: string;
};

type AddFloorPlanVersionInput = {
  originalName: string;
  mimeType: string;
  size: number;
  contents: Buffer;
  uploaderName: string;
  uploaderEmail: string;
};

type UpdateFloorPlanDetailsInput = {
  title: string;
  description: string;
  userEmail: string;
};

type FloorPlanInteractionUser = {
  email: string;
  name: string;
};

type FloorPlanMongoVersion = {
  _id?: ObjectId | string;
  versionNumber?: number;
  originalName?: string;
  fileId?: ObjectId | string;
  mimeType?: string;
  size?: number;
  uploadedAt?: Date | string;
  uploaderName?: string;
  uploaderEmail?: string;
};

type FloorPlanMongoReaction = {
  userEmail?: string;
  type?: FloorPlanReactionType;
  reactedAt?: Date | string;
};

type FloorPlanMongoCommentReply = {
  _id?: ObjectId | string;
  body?: string;
  userName?: string;
  userEmail?: string;
  createdAt?: Date | string;
};

type FloorPlanMongoComment = FloorPlanMongoCommentReply & {
  replies?: FloorPlanMongoCommentReply[];
};

type FloorPlanMongoDocument = {
  _id: ObjectId;
  title?: string;
  description?: string;
  originalName?: string;
  fileId?: ObjectId | string;
  mimeType?: string;
  size?: number;
  uploaderName?: string;
  uploaderEmail?: string;
  uploadedAt?: Date | string;
  isPublic?: boolean;
  studioData?: string;
  versions?: FloorPlanMongoVersion[];
  reactions?: FloorPlanMongoReaction[];
  comments?: FloorPlanMongoComment[];
};

export class FloorPlanInteractionError extends Error {
  constructor(
    public code:
      | "own-plan"
      | "not-owner"
      | "invalid-comment"
      | "missing-comment"
      | "invalid-details",
    message: string,
  ) {
    super(message);
    this.name = "FloorPlanInteractionError";
  }
}

const allowedExtensions = new Set([
  ".pdf",
  ".png",
  ".jpg",
  ".jpeg",
  ".webp",
  ".svg",
  ".json",
  ".ifc",
  ".zip",
  ".dwg",
  ".dxf",
]);

export const MAX_FLOOR_PLAN_UPLOAD_BYTES = 25 * 1024 * 1024;

function getDatabase() {
  const db = mongoose.connection.db;

  if (!db) {
    throw new Error("MongoDB connection is not ready");
  }

  return db;
}

function getBucket() {
  return new GridFSBucket(getDatabase(), { bucketName: "floorPlanFiles" });
}

function getPlansCollection() {
  return getDatabase().collection<FloorPlanMongoDocument>("floorplans");
}

function sanitizeFileName(value: string) {
  const parsed = path.parse(value);
  const name = parsed.name.replace(/[^a-zA-Z0-9-_]+/g, "-").replace(/^-+|-+$/g, "");
  const ext = parsed.ext.toLowerCase().replace(/[^a-z0-9.]/g, "");

  return `${name || "floor-plan"}${ext || ".bin"}`;
}

function normalizeEmail(email?: string | null) {
  return email?.toLowerCase().trim() ?? "";
}

function toIsoString(value: Date | string | undefined, fallback = new Date()) {
  if (value instanceof Date) {
    return value.toISOString();
  }

  if (typeof value === "string") {
    const parsed = new Date(value);
    if (Number.isFinite(parsed.getTime())) {
      return parsed.toISOString();
    }
  }

  return fallback.toISOString();
}

function getDateTime(value: Date | string | undefined) {
  if (value instanceof Date) {
    return value.getTime();
  }

  if (typeof value === "string") {
    const parsed = new Date(value).getTime();
    return Number.isFinite(parsed) ? parsed : 0;
  }

  return 0;
}

function toIdString(value: ObjectId | string | undefined) {
  return value ? value.toString() : new ObjectId().toString();
}

function toObjectId(value: ObjectId | string | undefined) {
  if (value instanceof ObjectId) {
    return value;
  }

  if (typeof value === "string" && ObjectId.isValid(value)) {
    return new ObjectId(value);
  }

  return null;
}

function serializeVersions(plan: FloorPlanMongoDocument): FloorPlanVersionRecord[] {
  const fallbackVersion: FloorPlanMongoVersion = {
    _id: plan.fileId ?? plan._id,
    versionNumber: 1,
    originalName: plan.originalName,
    fileId: plan.fileId,
    mimeType: plan.mimeType,
    size: plan.size,
    uploadedAt: plan.uploadedAt,
    uploaderName: plan.uploaderName,
    uploaderEmail: plan.uploaderEmail,
  };
  const sourceVersions = plan.versions?.length ? plan.versions : [fallbackVersion];
  const serialized = sourceVersions
    .map((version, index) => ({
      id: toIdString(version._id ?? version.fileId ?? plan._id),
      versionNumber:
        typeof version.versionNumber === "number" && version.versionNumber > 0
          ? version.versionNumber
          : index + 1,
      originalName: version.originalName ?? plan.originalName ?? "floor-plan",
      fileId: toIdString(version.fileId ?? plan.fileId),
      mimeType: version.mimeType ?? plan.mimeType ?? "application/octet-stream",
      size: version.size ?? plan.size ?? 0,
      uploadedAt: toIsoString(version.uploadedAt ?? plan.uploadedAt),
      uploaderName: version.uploaderName ?? plan.uploaderName ?? plan.uploaderEmail ?? "User",
      uploaderEmail: version.uploaderEmail ?? plan.uploaderEmail ?? "",
      isLatest: false,
    }))
    .sort((first, second) => first.versionNumber - second.versionNumber);

  return serialized.map((version, index) => ({
    ...version,
    isLatest: index === serialized.length - 1,
  }));
}

function serializeCommentReplies(replies: FloorPlanMongoCommentReply[] | undefined): FloorPlanCommentReplyRecord[] {
  return [...(replies ?? [])]
    .sort((first, second) => getDateTime(first.createdAt) - getDateTime(second.createdAt))
    .map((reply) => ({
      id: toIdString(reply._id),
      body: reply.body ?? "",
      userName: reply.userName ?? reply.userEmail ?? "User",
      userEmail: reply.userEmail ?? "",
      createdAt: toIsoString(reply.createdAt),
    }));
}

function serializeComments(plan: FloorPlanMongoDocument): FloorPlanCommentRecord[] {
  return [...(plan.comments ?? [])]
    .sort((first, second) => getDateTime(second.createdAt) - getDateTime(first.createdAt))
    .map((comment) => ({
      id: toIdString(comment._id),
      body: comment.body ?? "",
      userName: comment.userName ?? comment.userEmail ?? "User",
      userEmail: comment.userEmail ?? "",
      createdAt: toIsoString(comment.createdAt),
      replies: serializeCommentReplies(comment.replies),
    }));
}

function toRecord(plan: FloorPlanMongoDocument, currentUserEmail?: string | null): FloorPlanRecord {
  const currentEmail = normalizeEmail(currentUserEmail);
  const reactions = plan.reactions ?? [];
  const userReaction = reactions.find((reaction) => reaction.userEmail === currentEmail)?.type ?? null;
  const comments = serializeComments(plan);
  const versions = serializeVersions(plan);
  const latestVersion = versions[versions.length - 1];

  return {
    id: plan._id.toString(),
    title: plan.title ?? "Untitled floor plan",
    description: plan.description ?? "",
    originalName: latestVersion.originalName,
    fileId: latestVersion.fileId,
    mimeType: latestVersion.mimeType,
    size: latestVersion.size,
    uploaderName: plan.uploaderName ?? plan.uploaderEmail ?? "User",
    uploaderEmail: plan.uploaderEmail ?? "",
    uploadedAt: latestVersion.uploadedAt,
    isPublic: plan.isPublic ?? false,
    studioData: plan.studioData,
    likeCount: reactions.filter((reaction) => reaction.type === "like").length,
    dislikeCount: reactions.filter((reaction) => reaction.type === "dislike").length,
    userReaction,
    commentCount: comments.reduce((total, comment) => total + 1 + comment.replies.length, 0),
    comments,
    canInteract: Boolean(currentEmail && currentEmail !== normalizeEmail(plan.uploaderEmail)),
    canUploadVersion: Boolean(currentEmail && currentEmail === normalizeEmail(plan.uploaderEmail)),
    latestVersionNumber: latestVersion.versionNumber,
    versions,
  };
}

export function isAllowedFloorPlanFile(fileName: string) {
  return allowedExtensions.has(path.extname(fileName).toLowerCase());
}

export async function readFloorPlans(currentUserEmail?: string | null) {
  await connectDB();

  const plans = await getPlansCollection()
    .find({ isPublic: true })
    .sort({ uploadedAt: -1 })
    .toArray();
  return plans.map((plan) => toRecord(plan, currentUserEmail));
}

export async function readUserFloorPlans(currentUserEmail?: string | null) {
  const userEmail = normalizeEmail(currentUserEmail);

  if (!userEmail) {
    return [];
  }

  await connectDB();

  const plans = await getPlansCollection()
    .find({ uploaderEmail: userEmail })
    .sort({ uploadedAt: -1 })
    .toArray();
  return plans.map((plan) => toRecord(plan, userEmail));
}

export async function getFloorPlan(id: string, currentUserEmail?: string | null) {
  if (!ObjectId.isValid(id)) {
    return null;
  }

  await connectDB();

  const plan = await getPlansCollection().findOne({ _id: new ObjectId(id) });
  return plan ? toRecord(plan, currentUserEmail) : null;
}

export async function openFloorPlanDownload(
  id: string,
  versionId?: string,
): Promise<FloorPlanDownload | null> {
  if (!ObjectId.isValid(id)) {
    return null;
  }

  await connectDB();

  const plan = await getPlansCollection().findOne({ _id: new ObjectId(id) });
  if (!plan) {
    return null;
  }

  const versions = serializeVersions(plan);
  const selectedVersion = versionId
    ? versions.find(
        (version) => version.id === versionId || String(version.versionNumber) === versionId,
      )
    : versions[versions.length - 1];
  const fileId = toObjectId(selectedVersion?.fileId);

  if (!selectedVersion || !fileId) {
    return null;
  }

  const bucket = getBucket();
  const nodeStream = bucket.openDownloadStream(fileId);

  return {
    record: toRecord(plan),
    version: selectedVersion,
    stream: Readable.toWeb(nodeStream) as ReadableStream<Uint8Array>,
  };
}

export async function createFloorPlan(input: CreateFloorPlanInput) {
  await connectDB();

  const bucket = getBucket();
  const fileId = new ObjectId();
  const versionId = new ObjectId();
  const originalName = sanitizeFileName(input.originalName);
  const mimeType = input.mimeType || "application/octet-stream";
  const uploadStream = bucket.openUploadStreamWithId(fileId, originalName, {
    metadata: {
      mimeType,
      uploaderEmail: input.uploaderEmail,
      uploaderName: input.uploaderName,
    },
  });

  await finished(Readable.from(input.contents).pipe(uploadStream));

  try {
    const inserted = await getPlansCollection().insertOne({
      _id: new ObjectId(),
      title: input.title.trim() || path.parse(originalName).name,
      description: input.description.trim(),
      originalName,
      fileId,
      mimeType,
      size: input.size,
      uploaderName: input.uploaderName,
      uploaderEmail: normalizeEmail(input.uploaderEmail),
      uploadedAt: new Date(),
      isPublic: input.isPublic ?? false,
      ...(input.studioData ? { studioData: input.studioData } : {}),
      versions: [
        {
          _id: versionId,
          versionNumber: 1,
          originalName,
          fileId,
          mimeType,
          size: input.size,
          uploadedAt: new Date(),
          uploaderName: input.uploaderName,
          uploaderEmail: normalizeEmail(input.uploaderEmail),
        },
      ],
      reactions: [],
      comments: [],
    });

    const plan = await getFloorPlan(inserted.insertedId.toString(), input.uploaderEmail);

    if (!plan) {
      throw new Error("Floor plan metadata was not saved in MongoDB.");
    }

    return plan;
  } catch (error) {
    await bucket.delete(fileId).catch(() => undefined);
    throw error;
  }
}

export async function addFloorPlanVersion(id: string, input: AddFloorPlanVersionInput) {
  if (!ObjectId.isValid(id)) {
    return null;
  }

  await connectDB();

  const planId = new ObjectId(id);
  const plans = getPlansCollection();
  const plan = await plans.findOne({ _id: planId });

  if (!plan) {
    return null;
  }

  const uploaderEmail = normalizeEmail(input.uploaderEmail);

  if (normalizeEmail(plan.uploaderEmail) !== uploaderEmail) {
    throw new FloorPlanInteractionError(
      "not-owner",
      "Only the original uploader can add a new version.",
    );
  }

  const bucket = getBucket();
  const fileId = new ObjectId();
  const versionId = new ObjectId();
  const originalName = sanitizeFileName(input.originalName);
  const mimeType = input.mimeType || "application/octet-stream";
  const existingVersions: FloorPlanMongoVersion[] = plan.versions?.length
    ? plan.versions
    : [
        {
          _id: toObjectId(plan.fileId) ?? new ObjectId(),
          versionNumber: 1,
          originalName: plan.originalName,
          fileId: plan.fileId,
          mimeType: plan.mimeType,
          size: plan.size,
          uploadedAt: plan.uploadedAt,
          uploaderName: plan.uploaderName,
          uploaderEmail: plan.uploaderEmail,
        },
      ];
  const versionNumber =
    Math.max(
      ...existingVersions.map((version, index) =>
        typeof version.versionNumber === "number" && version.versionNumber > 0
          ? version.versionNumber
          : index + 1,
      ),
      0,
    ) + 1;
  const uploadedAt = new Date();
  const nextVersion = {
    _id: versionId,
    versionNumber,
    originalName,
    fileId,
    mimeType,
    size: input.size,
    uploadedAt,
    uploaderName: input.uploaderName,
    uploaderEmail,
  };
  const uploadStream = bucket.openUploadStreamWithId(fileId, originalName, {
    metadata: {
      mimeType,
      uploaderEmail,
      uploaderName: input.uploaderName,
      floorPlanId: id,
      versionNumber,
    },
  });

  await finished(Readable.from(input.contents).pipe(uploadStream));

  try {
    await plans.updateOne(
      { _id: planId },
      {
        $set: {
          originalName,
          fileId,
          mimeType,
          size: input.size,
          uploadedAt,
          versions: [...existingVersions, nextVersion],
        },
      },
    );

    return getFloorPlan(id, uploaderEmail);
  } catch (error) {
    await bucket.delete(fileId).catch(() => undefined);
    throw error;
  }
}

export async function updateFloorPlanDetails(id: string, input: UpdateFloorPlanDetailsInput) {
  if (!ObjectId.isValid(id)) {
    return null;
  }

  const title = input.title.trim();
  const description = input.description.trim();

  if (!title || title.length > 140 || description.length > 1000) {
    throw new FloorPlanInteractionError(
      "invalid-details",
      "Use a title between 1 and 140 characters and a description up to 1000 characters.",
    );
  }

  await connectDB();

  const planId = new ObjectId(id);
  const plans = getPlansCollection();
  const plan = await plans.findOne({ _id: planId });

  if (!plan) {
    return null;
  }

  const userEmail = normalizeEmail(input.userEmail);

  if (normalizeEmail(plan.uploaderEmail) !== userEmail) {
    throw new FloorPlanInteractionError(
      "not-owner",
      "Only the original uploader can edit this floor plan.",
    );
  }

  const updateFields: Partial<FloorPlanMongoDocument> = {
    title,
    description,
  };

  await plans.updateOne(
    { _id: planId },
    {
      $set: updateFields,
    },
  );

  return getFloorPlan(id, userEmail);
}

export async function deleteFloorPlan(id: string, userEmailInput: string) {
  if (!ObjectId.isValid(id)) {
    return null;
  }

  await connectDB();

  const planId = new ObjectId(id);
  const plans = getPlansCollection();
  const plan = await plans.findOne({ _id: planId });

  if (!plan) {
    return null;
  }

  const userEmail = normalizeEmail(userEmailInput);

  if (normalizeEmail(plan.uploaderEmail) !== userEmail) {
    throw new FloorPlanInteractionError(
      "not-owner",
      "Only the original uploader can delete this floor plan.",
    );
  }

  const bucket = getBucket();
  const fileIds = new Map<string, ObjectId>();

  for (const version of serializeVersions(plan)) {
    const fileId = toObjectId(version.fileId);

    if (fileId) {
      fileIds.set(fileId.toString(), fileId);
    }
  }

  const fallbackFileId = toObjectId(plan.fileId);

  if (fallbackFileId) {
    fileIds.set(fallbackFileId.toString(), fallbackFileId);
  }

  await plans.deleteOne({ _id: planId });
  await Promise.all(
    [...fileIds.values()].map((fileId) => bucket.delete(fileId).catch(() => undefined)),
  );

  return true;
}

export async function setFloorPlanPublic(id: string, userEmail: string, isPublic: boolean) {
  if (!ObjectId.isValid(id)) return null;

  await connectDB();

  const planId = new ObjectId(id);
  const plans = getPlansCollection();
  const plan = await plans.findOne({ _id: planId });

  if (!plan) return null;

  if (normalizeEmail(plan.uploaderEmail) !== normalizeEmail(userEmail)) {
    throw new FloorPlanInteractionError("not-owner", "Only the original uploader can publish or unpublish this plan.");
  }

  await plans.updateOne({ _id: planId }, { $set: { isPublic } });
  return getFloorPlan(id, userEmail);
}

export async function setFloorPlanReaction(
  id: string,
  user: FloorPlanInteractionUser,
  reactionType: FloorPlanReactionType | null,
) {
  if (!ObjectId.isValid(id)) {
    return null;
  }

  await connectDB();

  const planId = new ObjectId(id);
  const plans = getPlansCollection();
  const plan = await plans.findOne({ _id: planId });
  if (!plan) {
    return null;
  }

  const userEmail = normalizeEmail(user.email);
  await plans.updateOne({ _id: planId }, { $pull: { reactions: { userEmail } } });

  if (reactionType) {
    await plans.updateOne(
      { _id: planId },
      {
        $push: {
          reactions: {
            userEmail,
            type: reactionType,
            reactedAt: new Date(),
          },
        },
      },
    );
  }

  return getFloorPlan(id, userEmail);
}

export async function addFloorPlanComment(
  id: string,
  user: FloorPlanInteractionUser,
  body: string,
) {
  if (!ObjectId.isValid(id)) {
    return null;
  }

  const trimmedBody = body.trim();
  if (!trimmedBody || trimmedBody.length > 800) {
    throw new FloorPlanInteractionError(
      "invalid-comment",
      "Comments must be between 1 and 800 characters.",
    );
  }

  await connectDB();

  const planId = new ObjectId(id);
  const plans = getPlansCollection();
  const userEmail = normalizeEmail(user.email);
  const result = await plans.updateOne(
    { _id: planId },
    {
      $push: {
        comments: {
          _id: new ObjectId(),
          body: trimmedBody,
          userName: user.name.trim() || userEmail,
          userEmail,
          createdAt: new Date(),
          replies: [],
        },
      },
    },
  );

  if (!result.matchedCount) {
    return null;
  }

  return getFloorPlan(id, userEmail);
}

export async function addFloorPlanReply(
  id: string,
  user: FloorPlanInteractionUser,
  commentId: string,
  body: string,
) {
  if (!ObjectId.isValid(id) || !ObjectId.isValid(commentId)) {
    return null;
  }

  const trimmedBody = body.trim();
  if (!trimmedBody || trimmedBody.length > 800) {
    throw new FloorPlanInteractionError(
      "invalid-comment",
      "Replies must be between 1 and 800 characters.",
    );
  }

  await connectDB();

  const planId = new ObjectId(id);
  const parentCommentId = new ObjectId(commentId);
  const plans = getPlansCollection();
  const userEmail = normalizeEmail(user.email);
  const result = await plans.updateOne(
    { _id: planId, "comments._id": parentCommentId },
    {
      $push: {
        "comments.$.replies": {
          _id: new ObjectId(),
          body: trimmedBody,
          userName: user.name.trim() || userEmail,
          userEmail,
          createdAt: new Date(),
        },
      },
    },
  );

  if (!result.matchedCount) {
    const plan = await plans.findOne({ _id: planId });
    if (!plan) {
      return null;
    }

    throw new FloorPlanInteractionError("missing-comment", "Comment not found.");
  }

  return getFloorPlan(id, userEmail);
}
