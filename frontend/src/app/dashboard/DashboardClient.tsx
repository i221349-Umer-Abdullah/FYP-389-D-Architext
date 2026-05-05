"use client";

import {
  FormEvent,
  KeyboardEvent as ReactKeyboardEvent,
  MouseEvent,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import dynamic from "next/dynamic";

import type { FloorPlanReactionType, FloorPlanRecord } from "@/lib/floorPlans";

import styles from "./dashboard.module.css";

const FloorPlanJsonPreview = dynamic(
  () => import("./FloorPlanJsonPreview").then((module) => module.FloorPlanJsonPreview),
  {
    ssr: false,
    loading: () => <p className={styles.previewMessage}>Loading 3D preview...</p>,
  },
);

type DashboardClientProps = {
  initialFloorPlans: FloorPlanRecord[];
  mode?: "dashboard" | "library";
  currentUserEmail?: string;
};

type PreviewType = "image" | "pdf" | "json" | "unsupported";
type FileTypeFilter = "all" | "pdf" | "image" | "json" | "cad" | "project";
type DateFilter = "all" | "week" | "month" | "year";
type EngagementFilter = "all" | "liked" | "commented";
type SortOption = "newest" | "oldest" | "likes" | "comments" | "versions" | "title";

type EditDraft = {
  title: string;
  description: string;
};

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function getFileExtension(fileName: string) {
  const match = fileName.toLowerCase().match(/\.([a-z0-9]+)$/);
  return match?.[1] ?? "";
}

function getPreviewType(plan: FloorPlanRecord): PreviewType {
  const mimeType = plan.mimeType.toLowerCase();
  const extension = getFileExtension(plan.originalName);

  if (mimeType.startsWith("image/") || ["png", "jpg", "jpeg", "webp", "svg"].includes(extension)) {
    return "image";
  }

  if (mimeType === "application/pdf" || extension === "pdf") {
    return "pdf";
  }

  if (mimeType.includes("json") || extension === "json") {
    return "json";
  }

  return "unsupported";
}

function getFileTypeFilter(plan: FloorPlanRecord): Exclude<FileTypeFilter, "all"> {
  const mimeType = plan.mimeType.toLowerCase();
  const extension = getFileExtension(plan.originalName);
  const originalName = plan.originalName.toLowerCase();

  if (originalName.includes("architext-project")) {
    return "project";
  }

  if (mimeType === "application/pdf" || extension === "pdf") {
    return "pdf";
  }

  if (mimeType.startsWith("image/") || ["png", "jpg", "jpeg", "webp", "svg"].includes(extension)) {
    return "image";
  }

  if (mimeType.includes("json") || extension === "json") {
    return "json";
  }

  if (["dwg", "dxf", "ifc", "zip"].includes(extension)) {
    return "cad";
  }

  return "cad";
}

function getFileTypeLabel(plan: FloorPlanRecord) {
  const labels: Record<Exclude<FileTypeFilter, "all">, string> = {
    pdf: "PDF",
    image: "Image",
    json: "JSON",
    cad: "CAD",
    project: "Project",
  };

  return labels[getFileTypeFilter(plan)];
}

function isWithinDateFilter(uploadedAt: string, filter: DateFilter) {
  if (filter === "all") {
    return true;
  }

  const uploadedTime = new Date(uploadedAt).getTime();

  if (!Number.isFinite(uploadedTime)) {
    return false;
  }

  const days =
    filter === "week"
      ? 7
      : filter === "month"
        ? 30
        : 365;
  const cutoff = Date.now() - days * 24 * 60 * 60 * 1000;

  return uploadedTime >= cutoff;
}

function createEditDraft(plan: FloorPlanRecord): EditDraft {
  return {
    title: plan.title,
    description: plan.description,
  };
}

function isCardInteractiveTarget(target: EventTarget | null) {
  if (!(target instanceof Element)) {
    return false;
  }

  return Boolean(
    target.closest("a, button, input, textarea, select, label, form, [data-card-interactive='true']"),
  );
}

function LikeIcon() {
  return (
    <svg className={styles.reactionIcon} viewBox="0 0 24 24" aria-hidden="true">
      <path d="M7 10v10H4V10h3Zm3.1 10h6.7c.9 0 1.7-.6 1.9-1.5l1.1-5.3c.2-1.1-.6-2.2-1.7-2.2h-4.3l.7-3.3c.2-.9-.1-1.8-.7-2.4L13 4 8 9.4V18c0 1.1.9 2 2.1 2Z" />
    </svg>
  );
}

function DislikeIcon() {
  return (
    <svg className={styles.reactionIcon} viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M7 10v10H4V10h3Zm3.1 10h6.7c.9 0 1.7-.6 1.9-1.5l1.1-5.3c.2-1.1-.6-2.2-1.7-2.2h-4.3l.7-3.3c.2-.9-.1-1.8-.7-2.4L13 4 8 9.4V18c0 1.1.9 2 2.1 2Z"
        transform="rotate(180 12 12)"
      />
    </svg>
  );
}

function CommentIcon() {
  return (
    <svg className={styles.reactionIcon} viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 5h14v10H9l-4 4V5Zm2 2v7.2l1.2-1.2H17V7H7Z" />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg className={styles.commentButtonIcon} viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 12 20 5l-4 14-3.7-5.3L4 12Zm5.1.2 4 1.3 1.8 2.6 1.9-6.6-7.7 2.7Z" />
    </svg>
  );
}

function ReplyIcon() {
  return (
    <svg className={styles.commentButtonIcon} viewBox="0 0 24 24" aria-hidden="true">
      <path d="M10 7V3L3 10l7 7v-4h4.6c2.1 0 3.7 1.1 4.4 3 .2.5.4 1.2.5 2h1.8c0-2.8-.7-5-2.1-6.5C18 8.6 16.3 7 13.7 7H10Z" />
    </svg>
  );
}

function VersionIcon() {
  return (
    <svg className={styles.versionIcon} viewBox="0 0 24 24" aria-hidden="true">
      <path d="M7 3h10v3h3v15H4V6h3V3Zm2 3h6V5H9v1Zm-3 2v11h12V8H6Zm2 2h8v2H8v-2Zm0 4h6v2H8v-2Z" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg className={styles.trashIcon} viewBox="0 0 24 24" aria-hidden="true">
      <path d="M9 3h6l1 2h4v2H4V5h4L9 3Zm-3 5h12l-1 13H7L6 8Zm4 2v9h1v-9h-1Zm3 0v9h1v-9h-1Z" />
    </svg>
  );
}

export function DashboardClient({ initialFloorPlans, mode = "library", currentUserEmail = "" }: DashboardClientProps) {
  const [floorPlans, setFloorPlans] = useState(initialFloorPlans);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<FloorPlanRecord | null>(null);
  const [previewData, setPreviewData] = useState<unknown | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState("");
  const [show3D, setShow3D] = useState(false);
  const [isDownloadingIfc, setIsDownloadingIfc] = useState(false);
  const [interactionError, setInteractionError] = useState("");
  const [pendingReactionPlanId, setPendingReactionPlanId] = useState("");
  const [openCommentsPlanId, setOpenCommentsPlanId] = useState<string | null>(null);
  const [openVersionsPlanId, setOpenVersionsPlanId] = useState<string | null>(null);
  const [commentDrafts, setCommentDrafts] = useState<Record<string, string>>({});
  const [replyDrafts, setReplyDrafts] = useState<Record<string, string>>({});
  const [activeReplyCommentId, setActiveReplyCommentId] = useState("");
  const [pendingCommentKey, setPendingCommentKey] = useState("");
  const [pendingVersionPlanId, setPendingVersionPlanId] = useState("");
  const [editingPlanId, setEditingPlanId] = useState<string | null>(null);
  const [editDrafts, setEditDrafts] = useState<Record<string, EditDraft>>({});
  const [pendingEditPlanId, setPendingEditPlanId] = useState("");
  const [pendingDeletePlanId, setPendingDeletePlanId] = useState("");
  const [publishConfirmPlanId, setPublishConfirmPlanId] = useState("");
  const [pendingPublishPlanId, setPendingPublishPlanId] = useState("");
  const [myPlansOnly, setMyPlansOnly] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [fileTypeFilter, setFileTypeFilter] = useState<FileTypeFilter>("all");
  const [dateFilter, setDateFilter] = useState<DateFilter>("all");
  const [engagementFilter, setEngagementFilter] = useState<EngagementFilter>("all");
  const [sortOption, setSortOption] = useState<SortOption>("newest");
  const formRef = useRef<HTMLFormElement | null>(null);
  const isDashboardMode = mode === "dashboard";
  const isLibraryMode = mode === "library";
  const showUpload = isDashboardMode;
  const showLibrary = true;
  // Dashboard syncs all public plans; library syncs the user's own plans
  const floorPlansEndpoint = isDashboardMode ? "/api/floor-plans" : "/api/floor-plans?mine=1";
  const selectedPreviewType = selectedPlan ? getPreviewType(selectedPlan) : "unsupported";
  const studioDataParsed = useMemo(() => {
    if (!selectedPlan?.studioData) return null;
    try { return JSON.parse(selectedPlan.studioData) as Record<string, unknown>; } catch { return null; }
  }, [selectedPlan?.studioData]);
  const isStudioPlan = Boolean(studioDataParsed?.format === "architext-studio-project");
  const normalizedSearch = searchQuery.trim().toLowerCase();
  const filteredFloorPlans = floorPlans
    .filter((plan) => {
      if (isDashboardMode && myPlansOnly && plan.uploaderEmail !== currentUserEmail) return false;
      const searchableText = [
        plan.title,
        plan.description,
        plan.uploaderName,
        plan.uploaderEmail,
        plan.originalName,
        getFileTypeLabel(plan),
      ]
        .join(" ")
        .toLowerCase();
      const matchesSearch = !normalizedSearch || searchableText.includes(normalizedSearch);
      const matchesFileType =
        fileTypeFilter === "all" || getFileTypeFilter(plan) === fileTypeFilter;
      const matchesDate = isWithinDateFilter(plan.uploadedAt, dateFilter);
      const matchesEngagement =
        engagementFilter === "all" ||
        (engagementFilter === "liked" && plan.likeCount > 0) ||
        (engagementFilter === "commented" && plan.commentCount > 0);

      return matchesSearch && matchesFileType && matchesDate && matchesEngagement;
    })
    .sort((first, second) => {
      if (sortOption === "oldest") {
        return new Date(first.uploadedAt).getTime() - new Date(second.uploadedAt).getTime();
      }

      if (sortOption === "likes") {
        return second.likeCount - first.likeCount;
      }

      if (sortOption === "comments") {
        return second.commentCount - first.commentCount;
      }

      if (sortOption === "versions") {
        return second.latestVersionNumber - first.latestVersionNumber;
      }

      if (sortOption === "title") {
        return first.title.localeCompare(second.title);
      }

      return new Date(second.uploadedAt).getTime() - new Date(first.uploadedAt).getTime();
    });
  const visibleFloorPlans = [...filteredFloorPlans];
  const openSidePanelPlanId = openCommentsPlanId ?? openVersionsPlanId;
  const openSidePanelIndex = openSidePanelPlanId
    ? visibleFloorPlans.findIndex((plan) => plan.id === openSidePanelPlanId)
    : -1;

  if (openSidePanelIndex > 0 && openSidePanelIndex % 2 === 1) {
    const previousPlan = visibleFloorPlans[openSidePanelIndex - 1];
    visibleFloorPlans[openSidePanelIndex - 1] = visibleFloorPlans[openSidePanelIndex];
    visibleFloorPlans[openSidePanelIndex] = previousPlan;
  }

  useEffect(() => {
    if (!selectedPlan) {
      return;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        closePreview();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [selectedPlan]);

  useEffect(() => {
    setInteractionError("");
    setShow3D(false);
  }, [selectedPlan?.id]);

  useEffect(() => {
    if (!showLibrary) {
      return;
    }

    let active = true;

    async function syncFloorPlans() {
      try {
        const response = await fetch(floorPlansEndpoint, { cache: "no-store" });
        const payload = (await response.json()) as {
          floorPlans?: FloorPlanRecord[];
          error?: string;
        };

        if (!response.ok) {
          throw new Error(payload.error ?? "Could not refresh floor plans.");
        }

        if (active) {
          setFloorPlans(payload.floorPlans ?? []);
        }
      } catch (syncError) {
        if (active) {
          setInteractionError(
            syncError instanceof Error ? syncError.message : "Could not refresh floor plans.",
          );
        }
      }
    }

    function handleVisibilityChange() {
      if (document.visibilityState === "visible") {
        void syncFloorPlans();
      }
    }

    function handleFocus() {
      void syncFloorPlans();
    }

    void syncFloorPlans();
    window.addEventListener("focus", handleFocus);
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      active = false;
      window.removeEventListener("focus", handleFocus);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [floorPlansEndpoint, showLibrary]);

  useEffect(() => {
    if (!selectedPlan || getPreviewType(selectedPlan) !== "json") {
      setPreviewData(null);
      setPreviewLoading(false);
      setPreviewError("");
      return;
    }

    let active = true;

    async function loadJsonPreview() {
      setPreviewLoading(true);
      setPreviewError("");
      setPreviewData(null);

      try {
        const response = await fetch(`/api/floor-plans/${selectedPlan?.id}/view`, {
          cache: "no-store",
        });

        if (!response.ok) {
          throw new Error("Could not load preview.");
        }

        const rawText = await response.text();
        const parsed = JSON.parse(rawText) as unknown;

        if (active) setPreviewData(parsed);
      } catch (jsonError) {
        if (active) {
          setPreviewError(
            jsonError instanceof Error
              ? "This JSON file could not be turned into a 3D plan preview."
              : "Could not load preview.",
          );
        }
      } finally {
        if (active) {
          setPreviewLoading(false);
        }
      }
    }

    void loadJsonPreview();

    return () => {
      active = false;
    };
  }, [selectedPlan]);

  function mergeUpdatedFloorPlan(updatedPlan: FloorPlanRecord) {
    setFloorPlans((currentPlans) =>
      currentPlans.map((plan) => (plan.id === updatedPlan.id ? updatedPlan : plan)),
    );
    setSelectedPlan((currentPlan) => (currentPlan?.id === updatedPlan.id ? updatedPlan : currentPlan));
  }

  function removeFloorPlanFromState(planId: string) {
    setFloorPlans((currentPlans) => currentPlans.filter((plan) => plan.id !== planId));
    setSelectedPlan((currentPlan) => (currentPlan?.id === planId ? null : currentPlan));
    setOpenCommentsPlanId((currentPlanId) => (currentPlanId === planId ? null : currentPlanId));
    setOpenVersionsPlanId((currentPlanId) => (currentPlanId === planId ? null : currentPlanId));
    setEditingPlanId((currentPlanId) => (currentPlanId === planId ? null : currentPlanId));
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("");
    setError("");
    setIsUploading(true);

    const formData = new FormData(event.currentTarget);

    try {
      const response = await fetch("/api/floor-plans", {
        method: "POST",
        body: formData,
      });
      const payload = (await response.json()) as {
        floorPlan?: FloorPlanRecord;
        error?: string;
      };

      if (!response.ok) {
        throw new Error(payload.error ?? "Could not upload floor plan.");
      }

      if (!payload.floorPlan) {
        throw new Error("Upload completed, but MongoDB did not return the saved floor plan.");
      }

      formRef.current?.reset();
      setFloorPlans((currentPlans) => [
        payload.floorPlan as FloorPlanRecord,
        ...currentPlans.filter((plan) => plan.id !== payload.floorPlan?.id),
      ]);
      setStatus("Floor plan uploaded and published to the Dashboard.");
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Could not upload floor plan.");
    } finally {
      setIsUploading(false);
    }
  }

  function openPreview(plan: FloorPlanRecord) {
    setSelectedPlan(plan);
  }

  function closePreview() {
    setSelectedPlan(null);
    setPreviewData(null);
    setPreviewError("");
    setPreviewLoading(false);
  }

  function handleCardClick(event: MouseEvent<HTMLElement>, plan: FloorPlanRecord) {
    if (isCardInteractiveTarget(event.target)) {
      return;
    }

    openPreview(plan);
  }

  function handleCardKeyDown(event: ReactKeyboardEvent<HTMLElement>, plan: FloorPlanRecord) {
    if (isCardInteractiveTarget(event.target)) {
      return;
    }

    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openPreview(plan);
    }
  }

  function handleActionClick(event: MouseEvent<HTMLElement>) {
    event.stopPropagation();
  }

  async function handleReaction(plan: FloorPlanRecord, reactionType: FloorPlanReactionType) {
    if (!plan.canInteract) {
      setInteractionError("You can react only to plans uploaded by other users.");
      return;
    }

    const nextReaction = plan.userReaction === reactionType ? null : reactionType;
    setInteractionError("");
    setPendingReactionPlanId(plan.id);

    try {
      const response = await fetch(`/api/floor-plans/${plan.id}/reaction`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reaction: nextReaction }),
      });
      const payload = (await response.json()) as {
        floorPlan?: FloorPlanRecord;
        error?: string;
      };

      if (!response.ok || !payload.floorPlan) {
        throw new Error(payload.error ?? "Could not save reaction.");
      }

      mergeUpdatedFloorPlan(payload.floorPlan);
    } catch (reactionError) {
      setInteractionError(
        reactionError instanceof Error ? reactionError.message : "Could not save reaction.",
      );
    } finally {
      setPendingReactionPlanId("");
    }
  }

  function updateCommentDraft(planId: string, value: string) {
    setCommentDrafts((currentDrafts) => ({ ...currentDrafts, [planId]: value }));
  }

  function updateReplyDraft(commentId: string, value: string) {
    setReplyDrafts((currentDrafts) => ({ ...currentDrafts, [commentId]: value }));
  }

  async function submitComment(plan: FloorPlanRecord, parentCommentId?: string) {
    const body = (parentCommentId ? replyDrafts[parentCommentId] : commentDrafts[plan.id] ?? "").trim();

    if (!body) {
      setInteractionError(parentCommentId ? "Write a reply before posting." : "Write a comment before posting.");
      return;
    }

    const pendingKey = parentCommentId ? `reply:${parentCommentId}` : `comment:${plan.id}`;
    setInteractionError("");
    setPendingCommentKey(pendingKey);

    try {
      const response = await fetch(`/api/floor-plans/${plan.id}/comments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ body, parentCommentId }),
      });
      const payload = (await response.json()) as {
        floorPlan?: FloorPlanRecord;
        error?: string;
      };

      if (!response.ok || !payload.floorPlan) {
        throw new Error(payload.error ?? "Could not save comment.");
      }

      mergeUpdatedFloorPlan(payload.floorPlan);
      if (parentCommentId) {
        updateReplyDraft(parentCommentId, "");
        setActiveReplyCommentId("");
      } else {
        updateCommentDraft(plan.id, "");
      }
      setOpenCommentsPlanId(plan.id);
      setOpenVersionsPlanId(null);
    } catch (commentError) {
      setInteractionError(
        commentError instanceof Error ? commentError.message : "Could not save comment.",
      );
    } finally {
      setPendingCommentKey((currentKey) => (currentKey === pendingKey ? "" : currentKey));
    }
  }

  async function handleVersionUpload(event: FormEvent<HTMLFormElement>, plan: FloorPlanRecord) {
    event.preventDefault();

    if (!isDashboardMode || !plan.canUploadVersion) {
      setInteractionError("Only the original uploader can add a new version.");
      return;
    }

    const formData = new FormData(event.currentTarget);
    const file = formData.get("file");

    if (!(file instanceof File) || file.size <= 0) {
      setInteractionError("Choose a revised floor plan file.");
      return;
    }

    setInteractionError("");
    setPendingVersionPlanId(plan.id);

    try {
      const response = await fetch(`/api/floor-plans/${plan.id}/versions`, {
        method: "POST",
        body: formData,
      });
      const payload = (await response.json()) as {
        floorPlan?: FloorPlanRecord;
        error?: string;
      };

      if (!response.ok || !payload.floorPlan) {
        throw new Error(payload.error ?? "Could not upload this new version.");
      }

      event.currentTarget.reset();
      mergeUpdatedFloorPlan(payload.floorPlan);
      setOpenVersionsPlanId(plan.id);
      setStatus(`Version v${payload.floorPlan.latestVersionNumber} saved in MongoDB.`);
    } catch (versionError) {
      setInteractionError(
        versionError instanceof Error ? versionError.message : "Could not upload this new version.",
      );
    } finally {
      setPendingVersionPlanId("");
    }
  }

  function startEditingPlan(plan: FloorPlanRecord) {
    if (!isDashboardMode || !plan.canUploadVersion) {
      setInteractionError("Only the original uploader can edit this floor plan.");
      return;
    }

    setInteractionError("");
    setOpenCommentsPlanId(null);
    setOpenVersionsPlanId(null);
    setEditingPlanId((currentPlanId) => (currentPlanId === plan.id ? null : plan.id));
    setEditDrafts((currentDrafts) => ({
      ...currentDrafts,
      [plan.id]: currentDrafts[plan.id] ?? createEditDraft(plan),
    }));
  }

  function updateEditDraft(planId: string, field: keyof EditDraft, value: string) {
    setEditDrafts((currentDrafts) => ({
      ...currentDrafts,
      [planId]: {
        title: currentDrafts[planId]?.title ?? "",
        description: currentDrafts[planId]?.description ?? "",
        [field]: value,
      },
    }));
  }

  async function handleEditSubmit(event: FormEvent<HTMLFormElement>, plan: FloorPlanRecord) {
    event.preventDefault();

    if (!isDashboardMode || !plan.canUploadVersion) {
      setInteractionError("Only the original uploader can edit this floor plan.");
      return;
    }

    const draft = editDrafts[plan.id] ?? createEditDraft(plan);

    if (!draft.title.trim()) {
      setInteractionError("Add a title before saving changes.");
      return;
    }

    setInteractionError("");
    setPendingEditPlanId(plan.id);

    try {
      const response = await fetch(`/api/floor-plans/${plan.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: draft.title,
          description: draft.description,
        }),
      });
      const payload = (await response.json()) as {
        floorPlan?: FloorPlanRecord;
        error?: string;
      };

      if (!response.ok || !payload.floorPlan) {
        throw new Error(payload.error ?? "Could not update this floor plan.");
      }

      mergeUpdatedFloorPlan(payload.floorPlan);
      setEditingPlanId(null);
      setStatus("Floor plan details updated.");
    } catch (editError) {
      setInteractionError(editError instanceof Error ? editError.message : "Could not update this floor plan.");
    } finally {
      setPendingEditPlanId("");
    }
  }

  async function handleDeletePlan(plan: FloorPlanRecord) {
    if (!plan.canUploadVersion) {
      setInteractionError("Only the original uploader can delete this floor plan.");
      return;
    }

    if (isDashboardMode) {
      // Dashboard delete = unpublish (remove from public view, keep in library)
      setInteractionError("");
      setPendingDeletePlanId(plan.id);
      try {
        const response = await fetch(`/api/floor-plans/${plan.id}/publish`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ isPublic: false }),
        });
        const payload = (await response.json().catch(() => ({}))) as { error?: string };
        if (!response.ok) throw new Error(payload.error ?? "Could not remove from Dashboard.");
        removeFloorPlanFromState(plan.id);
        setStatus("Plan removed from Dashboard. It is still in your Library.");
      } catch (err) {
        setInteractionError(err instanceof Error ? err.message : "Could not remove from Dashboard.");
      } finally {
        setPendingDeletePlanId("");
      }
      return;
    }

    // Library delete = full permanent delete
    const confirmed = window.confirm(
      `Delete "${plan.title}" and all of its saved versions? This cannot be undone.`,
    );
    if (!confirmed) return;

    setInteractionError("");
    setPendingDeletePlanId(plan.id);
    try {
      const response = await fetch(`/api/floor-plans/${plan.id}`, { method: "DELETE" });
      const payload = (await response.json().catch(() => ({}))) as { error?: string };
      if (!response.ok) throw new Error(payload.error ?? "Could not delete this floor plan.");
      removeFloorPlanFromState(plan.id);
      setStatus("Floor plan deleted.");
    } catch (deleteError) {
      setInteractionError(
        deleteError instanceof Error ? deleteError.message : "Could not delete this floor plan.",
      );
    } finally {
      setPendingDeletePlanId("");
    }
  }

  async function handlePublishPlan(plan: FloorPlanRecord) {
    setInteractionError("");
    setPendingPublishPlanId(plan.id);
    try {
      const response = await fetch(`/api/floor-plans/${plan.id}/publish`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ isPublic: true }),
      });
      const payload = (await response.json()) as { floorPlan?: FloorPlanRecord; error?: string };
      if (!response.ok || !payload.floorPlan) throw new Error(payload.error ?? "Could not publish.");
      mergeUpdatedFloorPlan(payload.floorPlan);
      setStatus("Plan published to Dashboard. Everyone can now see it.");
    } catch (err) {
      setInteractionError(err instanceof Error ? err.message : "Could not publish plan.");
    } finally {
      setPendingPublishPlanId("");
      setPublishConfirmPlanId("");
    }
  }

  function handleCommentSubmit(event: FormEvent<HTMLFormElement>, plan: FloorPlanRecord) {
    event.preventDefault();
    void submitComment(plan);
  }

  function handleReplySubmit(
    event: FormEvent<HTMLFormElement>,
    plan: FloorPlanRecord,
    commentId: string,
  ) {
    event.preventDefault();
    void submitComment(plan, commentId);
  }

  function renderEditForm(plan: FloorPlanRecord) {
    const draft = editDrafts[plan.id] ?? createEditDraft(plan);
    const isSaving = pendingEditPlanId === plan.id;

    return (
      <form
        className={styles.editForm}
        data-card-interactive="true"
        onSubmit={(event) => handleEditSubmit(event, plan)}
        onClick={handleActionClick}
      >
        <label className={styles.field}>
          <span className={styles.label}>Project title</span>
          <input
            className={styles.input}
            type="text"
            value={draft.title}
            maxLength={140}
            required
            disabled={isSaving}
            onChange={(event) => updateEditDraft(plan.id, "title", event.target.value)}
          />
        </label>
        <label className={styles.field}>
          <span className={styles.label}>Short description</span>
          <textarea
            className={styles.textarea}
            value={draft.description}
            maxLength={1000}
            rows={3}
            disabled={isSaving}
            onChange={(event) => updateEditDraft(plan.id, "description", event.target.value)}
          />
        </label>
        <div className={styles.editFormActions}>
          <button type="submit" className={styles.versionUploadButton} disabled={isSaving}>
            {isSaving ? "Saving..." : "Save Changes"}
          </button>
          <button
            type="button"
            className={styles.ownerActionButton}
            disabled={isSaving}
            onClick={(event) => {
              handleActionClick(event);
              setEditingPlanId(null);
            }}
          >
            Cancel
          </button>
        </div>
      </form>
    );
  }

  function renderCommentPanel(plan: FloorPlanRecord, mode: "inline" | "modal" = "inline", readOnly = false) {
    const commentDraft = commentDrafts[plan.id] ?? "";
    const isPostingComment = pendingCommentKey === `comment:${plan.id}`;
    const panelClassName = mode === "modal" ? styles.discussionSection : styles.inlineCommentPanel;

    return (
      <section
        className={panelClassName}
        data-card-interactive="true"
        onClick={handleActionClick}
        onKeyDown={(event) => event.stopPropagation()}
      >
        <div className={styles.discussionHeader}>
          <div>
            <p className={styles.kicker}>Comments</p>
            <h3 className={styles.discussionTitle}>Plan discussion</h3>
          </div>
          {mode === "modal" && !readOnly ? renderReactionControls(plan) : null}
          {mode === "modal" && readOnly ? (
            <div className={styles.reactionCounts}>
              <span>{plan.likeCount} {plan.likeCount === 1 ? "like" : "likes"}</span>
              <span>{plan.dislikeCount} {plan.dislikeCount === 1 ? "dislike" : "dislikes"}</span>
            </div>
          ) : null}
        </div>

        {!readOnly ? (
          <form className={styles.commentForm} onSubmit={(event) => handleCommentSubmit(event, plan)}>
            <label className={styles.field}>
              <span className={styles.label}>Add a comment</span>
              <textarea
                className={styles.textarea}
                value={commentDraft}
                maxLength={800}
                rows={mode === "modal" ? 3 : 2}
                placeholder="Share a review note for this floor plan."
                disabled={isPostingComment}
                onChange={(event) => updateCommentDraft(plan.id, event.target.value)}
              />
            </label>
            <div className={styles.commentFormFooter}>
              <span>{commentDraft.length}/800</span>
              <button
                type="submit"
                className={styles.commentButton}
                disabled={isPostingComment}
                aria-label={isPostingComment ? "Posting comment" : "Post comment"}
                title={isPostingComment ? "Posting" : "Post"}
              >
                <SendIcon />
              </button>
            </div>
          </form>
        ) : null}

        <div className={styles.commentList}>
          {plan.comments.length ? (
            plan.comments.map((comment) => {
              const replyDraft = replyDrafts[comment.id] ?? "";
              const isReplying = activeReplyCommentId === comment.id;
              const isPostingReply = pendingCommentKey === `reply:${comment.id}`;

              return (
                <article key={comment.id} className={styles.commentItem}>
                  <div className={styles.commentMeta}>
                    <strong>{comment.userName}</strong>
                    <time dateTime={comment.createdAt}>{formatDate(comment.createdAt)}</time>
                  </div>
                  <p>{comment.body}</p>

                  {!readOnly ? (
                    <button
                      type="button"
                      className={styles.replyButton}
                      aria-label={`Reply to ${comment.userName}`}
                      title="Reply"
                      onClick={(event) => {
                        handleActionClick(event);
                        setActiveReplyCommentId((currentId) =>
                          currentId === comment.id ? "" : comment.id,
                        );
                      }}
                    >
                      <ReplyIcon />
                    </button>
                  ) : null}

                  {comment.replies.length ? (
                    <div className={styles.replyList}>
                      {comment.replies.map((reply) => (
                        <article key={reply.id} className={styles.replyItem}>
                          <div className={styles.commentMeta}>
                            <strong>{reply.userName}</strong>
                            <time dateTime={reply.createdAt}>{formatDate(reply.createdAt)}</time>
                          </div>
                          <p>{reply.body}</p>
                        </article>
                      ))}
                    </div>
                  ) : null}

                  {isReplying && !readOnly ? (
                    <form
                      className={styles.replyForm}
                      onSubmit={(event) => handleReplySubmit(event, plan, comment.id)}
                    >
                      <textarea
                        className={styles.textarea}
                        value={replyDraft}
                        maxLength={800}
                        rows={2}
                        placeholder={`Reply to ${comment.userName}`}
                        disabled={isPostingReply}
                        onChange={(event) => updateReplyDraft(comment.id, event.target.value)}
                      />
                      <div className={styles.commentFormFooter}>
                        <span>{replyDraft.length}/800</span>
                        <button
                          type="submit"
                          className={styles.commentButton}
                          disabled={isPostingReply}
                          aria-label={isPostingReply ? "Posting reply" : "Post reply"}
                          title={isPostingReply ? "Posting" : "Post reply"}
                        >
                          <SendIcon />
                        </button>
                      </div>
                    </form>
                  ) : null}
                </article>
              );
            })
          ) : (
            <p className={styles.emptyComments}>{readOnly ? "No comments on this plan." : "No comments yet."}</p>
          )}
        </div>
      </section>
    );
  }

  function renderVersionPanel(plan: FloorPlanRecord) {
    const sortedVersions = [...plan.versions].sort(
      (first, second) => second.versionNumber - first.versionNumber,
    );
    const latestVersion = sortedVersions[0];
    const previousVersion = sortedVersions[1];
    const sizeDelta = latestVersion && previousVersion ? latestVersion.size - previousVersion.size : 0;
    const isUploadingVersion = pendingVersionPlanId === plan.id;

    return (
      <section
        className={styles.versionPanel}
        data-card-interactive="true"
        onClick={handleActionClick}
        onKeyDown={(event) => event.stopPropagation()}
      >
        <div className={styles.versionHeader}>
          <div>
            <p className={styles.kicker}>Version history</p>
            <h3 className={styles.versionTitle}>Latest v{plan.latestVersionNumber}</h3>
          </div>
          <span className={styles.versionCount}>{plan.versions.length} versions</span>
        </div>

        {latestVersion && previousVersion ? (
          <p className={styles.versionNote}>
            v{latestVersion.versionNumber} after v{previousVersion.versionNumber}:{" "}
            {latestVersion.originalName} is {Math.abs(sizeDelta) ? formatBytes(Math.abs(sizeDelta)) : "0 B"}{" "}
            {sizeDelta > 0 ? "larger" : sizeDelta < 0 ? "smaller" : "the same size"}.
          </p>
        ) : (
          <p className={styles.versionNote}>This plan has only the original v1 upload.</p>
        )}

        {isDashboardMode && plan.canUploadVersion ? (
          <form className={styles.versionUploadForm} onSubmit={(event) => handleVersionUpload(event, plan)}>
            <label className={styles.field}>
              <span className={styles.label}>Upload v{plan.latestVersionNumber + 1}</span>
              <input
                className={styles.fileInput}
                type="file"
                name="file"
                accept=".pdf,.png,.jpg,.jpeg,.webp,.svg,.json,.ifc,.zip,.dwg,.dxf"
                required
                disabled={isUploadingVersion}
              />
            </label>
            <button type="submit" className={styles.versionUploadButton} disabled={isUploadingVersion}>
              {isUploadingVersion ? "Uploading..." : "Upload New Version"}
            </button>
          </form>
        ) : null}

        <div className={styles.versionList}>
          {sortedVersions.map((version) => (
            <article key={version.id} className={styles.versionItem}>
              <div>
                <span className={styles.versionBadge}>v{version.versionNumber}</span>
                {version.isLatest ? <span className={styles.latestBadge}>Latest</span> : null}
              </div>
              <div className={styles.versionMeta}>
                <strong>{version.originalName}</strong>
                <span>
                  {formatBytes(version.size)} - {formatDate(version.uploadedAt)}
                </span>
              </div>
              <a
                className={styles.versionDownload}
                href={`/api/floor-plans/${plan.id}/versions/${version.id}/download`}
                download
              >
                Download
              </a>
            </article>
          ))}
        </div>
      </section>
    );
  }

  function renderReactionControls(plan: FloorPlanRecord) {
    const isPending = pendingReactionPlanId === plan.id;
    const likeClassName = `${styles.reactionButton} ${
      plan.userReaction === "like" ? styles.reactionButtonActive : ""
    }`;
    const dislikeClassName = `${styles.reactionButton} ${
      plan.userReaction === "dislike" ? styles.reactionButtonActive : ""
    }`;
    const commentClassName = `${styles.reactionButton} ${
      openCommentsPlanId === plan.id ? styles.reactionButtonActive : ""
    }`;
    const disabledTitle = plan.canInteract
      ? undefined
      : "You can react only to plans uploaded by other users.";

    return (
      <div className={styles.reactionControls} onClick={handleActionClick}>
        <button
          type="button"
          className={likeClassName}
          aria-label={`Like plan. ${plan.likeCount} likes`}
          aria-pressed={plan.userReaction === "like"}
          title={disabledTitle ?? "Like"}
          disabled={!plan.canInteract || isPending}
          onClick={(event) => {
            handleActionClick(event);
            void handleReaction(plan, "like");
          }}
        >
          <LikeIcon />
          <span>{plan.likeCount}</span>
        </button>
        <button
          type="button"
          className={dislikeClassName}
          aria-label={`Dislike plan. ${plan.dislikeCount} dislikes`}
          aria-pressed={plan.userReaction === "dislike"}
          title={disabledTitle ?? "Dislike"}
          disabled={!plan.canInteract || isPending}
          onClick={(event) => {
            handleActionClick(event);
            void handleReaction(plan, "dislike");
          }}
        >
          <DislikeIcon />
          <span>{plan.dislikeCount}</span>
        </button>
        <button
          type="button"
          className={commentClassName}
          aria-label={`${openCommentsPlanId === plan.id ? "Close" : "Open"} comments. ${
            plan.commentCount
          } ${plan.commentCount === 1 ? "comment" : "comments"}`}
          title="Comments"
          onClick={(event) => {
            handleActionClick(event);
            setOpenCommentsPlanId((currentPlanId) =>
              currentPlanId === plan.id ? null : plan.id,
            );
            setOpenVersionsPlanId(null);
            setEditingPlanId(null);
          }}
        >
          <CommentIcon />
          <span>{plan.commentCount}</span>
        </button>
      </div>
    );
  }

  async function downloadStudioIfc() {
    if (!studioDataParsed) return;
    const rooms = studioDataParsed.rooms as unknown[] | undefined;
    if (!rooms?.length) return;
    setIsDownloadingIfc(true);
    try {
      const api = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const res = await fetch(`${api}/api/ifc-from-rooms`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rooms, prompt: studioDataParsed.prompt }),
      });
      if (!res.ok) throw new Error("IFC generation failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "architext-floor-plan.ifc";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // silently ignore — user will see the button re-enable
    } finally {
      setIsDownloadingIfc(false);
    }
  }

  function renderPreviewContent(plan: FloorPlanRecord) {
    const viewUrl = `/api/floor-plans/${plan.id}/view`;

    if (selectedPreviewType === "image") {
      // Studio-generated plans: show 2D floor plan image with 3D toggle
      if (isStudioPlan) {
        if (show3D && studioDataParsed) {
          return <FloorPlanJsonPreview data={studioDataParsed} title={plan.title} />;
        }
        return (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={viewUrl} alt={plan.title} className={styles.previewImage} />
        );
      }
      return (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={viewUrl} alt={plan.title} className={styles.previewImage} />
      );
    }

    if (selectedPreviewType === "pdf") {
      return <iframe src={viewUrl} title={plan.title} className={styles.previewFrame} />;
    }

    if (selectedPreviewType === "json") {
      if (previewLoading) {
        return <p className={styles.previewMessage}>Loading plan preview...</p>;
      }

      if (previewError) {
        return <p className={styles.previewMessage}>{previewError}</p>;
      }

      if (previewData) {
        return <FloorPlanJsonPreview data={previewData} title={plan.title} />;
      }

      return <p className={styles.previewMessage}>Preparing 3D plan preview...</p>;
    }

    return (
      <div className={styles.unsupportedPreview}>
        <p className={styles.previewMessage}>
          Browser preview is not available for this file type. Download the plan to open it
          in the right design tool.
        </p>
      </div>
    );
  }

  return (
    <div className={styles.dashboard}>
      {showUpload ? (
      <section className={styles.uploadSection}>
        <div>
          <p className={styles.kicker}>Dashboard</p>
          <h1 className={styles.title}>Upload a floor plan.</h1>
          <p className={styles.subtitle}>
            Add PDF, image, IFC, CAD, JSON, or ZIP files. Every logged-in user can download
            uploaded plans from the Floor Plans page.
          </p>
        </div>

        <form ref={formRef} className={styles.uploadForm} onSubmit={handleUpload}>
          <label className={styles.field}>
            <span className={styles.label}>Project title</span>
            <input
              className={styles.input}
              type="text"
              name="title"
              placeholder="Residential floor plan"
              required
              disabled={isUploading}
            />
          </label>

          <label className={styles.field}>
            <span className={styles.label}>Short description</span>
            <textarea
              className={styles.textarea}
              name="description"
              rows={4}
              placeholder="Ground floor plan, 5 marla, ready for review."
              disabled={isUploading}
            />
          </label>

          <label className={styles.field}>
            <span className={styles.label}>Floor plan file</span>
            <input
              className={styles.fileInput}
              type="file"
              name="file"
              accept=".pdf,.png,.jpg,.jpeg,.webp,.svg,.json,.ifc,.zip,.dwg,.dxf"
              required
              disabled={isUploading}
            />
          </label>

          <input type="hidden" name="isPublic" value="true" />

          {error ? <p className={styles.error}>{error}</p> : null}
          {status ? <p className={styles.status}>{status}</p> : null}

          <button type="submit" className={styles.submitButton} disabled={isUploading}>
            {isUploading ? "Uploading..." : "Upload Floor Plan"}
          </button>
        </form>
      </section>
      ) : null}

      {showLibrary ? (
      <section className={styles.librarySection}>
        <div className={styles.libraryHeader}>
          <div>
            <p className={styles.kicker}>{isDashboardMode ? "Public Repository" : "My Library"}</p>
            <h2 className={styles.sectionTitle}>
              {isDashboardMode ? "Public floor plans" : "Saved plans"}
            </h2>
            <p className={styles.subtitle}>
              {isDashboardMode
                ? "All publicly shared floor plans. Upload above to contribute."
                : "Floor plans you have saved. Publish any plan to share it on the Dashboard."}
            </p>
          </div>
          {isDashboardMode ? (
            <button
              type="button"
              className={`${styles.ownerActionButton} ${myPlansOnly ? styles.reactionButtonActive : ""}`}
              onClick={() => setMyPlansOnly((v) => !v)}
            >
              {myPlansOnly ? "All Plans" : "My Plans Only"}
            </button>
          ) : null}
        </div>

        <div className={styles.libraryTools} data-card-interactive="true">
          <div className={styles.libraryToolsHeader}>
            <button
              type="button"
              className={styles.ownerActionButton}
              onClick={() => {
                setSearchQuery("");
                setFileTypeFilter("all");
                setDateFilter("all");
                setEngagementFilter("all");
                setSortOption("newest");
              }}
            >
              Reset Filters
            </button>
          </div>
          <label className={`${styles.field} ${styles.searchField}`}>
            <span className={styles.label}>Search title, uploader, or file type</span>
            <input
              className={styles.input}
              type="search"
              value={searchQuery}
              placeholder="Search library"
              onChange={(event) => setSearchQuery(event.target.value)}
            />
          </label>
          <div className={styles.filterGrid}>
            <label className={styles.field}>
              <span className={styles.label}>File type</span>
              <select
                className={styles.select}
                value={fileTypeFilter}
                onChange={(event) => setFileTypeFilter(event.target.value as FileTypeFilter)}
              >
                <option value="all">All files</option>
                <option value="project">Project JSON</option>
                <option value="pdf">PDF</option>
                <option value="image">Images</option>
                <option value="json">JSON</option>
                <option value="cad">CAD / IFC / ZIP</option>
              </select>
            </label>
            <label className={styles.field}>
              <span className={styles.label}>Date</span>
              <select
                className={styles.select}
                value={dateFilter}
                onChange={(event) => setDateFilter(event.target.value as DateFilter)}
              >
                <option value="all">Any date</option>
                <option value="week">Last 7 days</option>
                <option value="month">Last 30 days</option>
                <option value="year">Last year</option>
              </select>
            </label>
            <label className={styles.field}>
              <span className={styles.label}>Activity</span>
              <select
                className={styles.select}
                value={engagementFilter}
                onChange={(event) => setEngagementFilter(event.target.value as EngagementFilter)}
              >
                <option value="all">Any activity</option>
                <option value="liked">Has likes</option>
                <option value="commented">Has comments</option>
              </select>
            </label>
            <label className={styles.field}>
              <span className={styles.label}>Sort</span>
              <select
                className={styles.select}
                value={sortOption}
                onChange={(event) => setSortOption(event.target.value as SortOption)}
              >
                <option value="newest">Newest date</option>
                <option value="oldest">Oldest date</option>
                <option value="likes">Most liked</option>
                <option value="comments">Most comments</option>
                <option value="versions">Most versions</option>
                <option value="title">Project title</option>
              </select>
            </label>
          </div>
          <p className={styles.resultSummary}>
            Showing {filteredFloorPlans.length} of {floorPlans.length} floor plans.
          </p>
        </div>

        {interactionError ? <p className={styles.error}>{interactionError}</p> : null}

        {filteredFloorPlans.length ? (
          <div className={styles.planGrid}>
            {visibleFloorPlans.map((plan) => (
              <article
                key={plan.id}
                className={`${styles.planCard} ${
                  openSidePanelPlanId === plan.id ? styles.planCardWithComments : ""
                }`}
                role="button"
                tabIndex={0}
                onClick={(event) => handleCardClick(event, plan)}
                onKeyDown={(event) => handleCardKeyDown(event, plan)}
              >
                <button
                  type="button"
                  className={`${styles.versionCornerButton} ${
                    openVersionsPlanId === plan.id ? styles.versionCornerButtonActive : ""
                  }`}
                  aria-label={`Open version history. Latest version v${plan.latestVersionNumber}`}
                  title={`Versions: latest v${plan.latestVersionNumber}`}
                  onClick={(event) => {
                    handleActionClick(event);
                    setOpenVersionsPlanId((currentPlanId) =>
                      currentPlanId === plan.id ? null : plan.id,
                    );
                    setOpenCommentsPlanId(null);
                    setEditingPlanId(null);
                  }}
                >
                  <VersionIcon />
                  <span>{plan.latestVersionNumber}</span>
                </button>
                <div className={styles.planCardBody}>
                  <div>
                    <p className={styles.planTitle}>{plan.title}</p>
                    <p className={styles.planDescription}>
                      {plan.description || "No description added."}
                    </p>
                  </div>
                  <dl className={styles.planMeta}>
                    <div>
                      <dt>Uploaded by</dt>
                      <dd>{plan.uploaderName}</dd>
                    </div>
                    <div>
                      <dt>File</dt>
                      <dd>
                        {plan.originalName} - {formatBytes(plan.size)}
                      </dd>
                    </div>
                    <div>
                      <dt>Type</dt>
                      <dd>{getFileTypeLabel(plan)}</dd>
                    </div>
                    <div>
                      <dt>Date</dt>
                      <dd>{formatDate(plan.uploadedAt)}</dd>
                    </div>
                    <div>
                      <dt>Version</dt>
                      <dd>v{plan.latestVersionNumber}</dd>
                    </div>
                  </dl>
                  {isDashboardMode && plan.canUploadVersion ? (
                    <div className={styles.ownerActions} data-card-interactive="true">
                      <button
                        type="button"
                        className={styles.ownerActionButton}
                        onClick={(event) => {
                          handleActionClick(event);
                          startEditingPlan(plan);
                        }}
                      >
                        {editingPlanId === plan.id ? "Close Edit" : "Edit Details"}
                      </button>
                      <button
                        type="button"
                        className={styles.ownerActionButton}
                        disabled={pendingDeletePlanId === plan.id}
                        onClick={(event) => {
                          handleActionClick(event);
                          void handleDeletePlan(plan);
                        }}
                      >
                        {pendingDeletePlanId === plan.id ? "Removing..." : "Remove from Dashboard"}
                      </button>
                    </div>
                  ) : null}
                  {isLibraryMode && plan.canUploadVersion ? (
                    <div className={styles.ownerActions} data-card-interactive="true">
                      {plan.isPublic ? (
                        <span className={styles.publicBadge}>Published to Dashboard</span>
                      ) : publishConfirmPlanId === plan.id ? (
                        <div className={styles.publishConfirm}>
                          <p className={styles.publishConfirmText}>
                            This will make your plan visible to everyone on the Dashboard. Are you sure?
                          </p>
                          <div className={styles.publishConfirmActions}>
                            <button
                              type="button"
                              className={styles.versionUploadButton}
                              disabled={pendingPublishPlanId === plan.id}
                              onClick={(event) => {
                                handleActionClick(event);
                                void handlePublishPlan(plan);
                              }}
                            >
                              {pendingPublishPlanId === plan.id ? "Publishing..." : "Yes, Publish"}
                            </button>
                            <button
                              type="button"
                              className={styles.ownerActionButton}
                              disabled={pendingPublishPlanId === plan.id}
                              onClick={(event) => {
                                handleActionClick(event);
                                setPublishConfirmPlanId("");
                              }}
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        <button
                          type="button"
                          className={styles.ownerActionButton}
                          onClick={(event) => {
                            handleActionClick(event);
                            setPublishConfirmPlanId(plan.id);
                          }}
                        >
                          Publish to Dashboard
                        </button>
                      )}
                    </div>
                  ) : null}
                  {editingPlanId === plan.id ? renderEditForm(plan) : null}
                  {isDashboardMode ? renderReactionControls(plan) : null}
                  <div className={styles.planActions}>
                    <button
                      type="button"
                      className={styles.viewButton}
                      onClick={(event) => {
                        handleActionClick(event);
                        openPreview(plan);
                      }}
                    >
                      View Plan
                    </button>
                    <a
                      className={styles.downloadButton}
                      href={`/api/floor-plans/${plan.id}/download`}
                      download
                      onClick={handleActionClick}
                    >
                      Download Plan
                    </a>
                  </div>
                </div>
                {openCommentsPlanId === plan.id && isDashboardMode ? renderCommentPanel(plan) : null}
                {openVersionsPlanId === plan.id ? renderVersionPanel(plan) : null}
                {isLibraryMode && plan.canUploadVersion ? (
                  <button
                    type="button"
                    className={styles.trashCornerButton}
                    aria-label="Delete plan"
                    title="Delete plan"
                    disabled={pendingDeletePlanId === plan.id}
                    data-card-interactive="true"
                    onClick={(event) => {
                      handleActionClick(event);
                      void handleDeletePlan(plan);
                    }}
                  >
                    <TrashIcon />
                  </button>
                ) : null}
              </article>
            ))}
          </div>
        ) : (
          <p className={styles.emptyState}>
            {isDashboardMode
              ? myPlansOnly
                ? "You have not published any floor plans to the Dashboard yet."
                : "No public floor plans yet. Be the first to upload one above."
              : "You have no saved floor plans yet. Generate one in the Studio to get started."}
          </p>
        )}
      </section>
      ) : null}

      {showLibrary && selectedPlan ? (
        <div className={styles.modalOverlay} role="presentation" onClick={closePreview}>
          <section
            className={styles.modal}
            role="dialog"
            aria-modal="true"
            aria-labelledby="floor-plan-preview-title"
            onClick={(event) => event.stopPropagation()}
          >
            <div className={styles.modalHeader}>
              <div>
                <p className={styles.kicker}>Plan preview</p>
                <h2 id="floor-plan-preview-title" className={styles.modalTitle}>
                  {selectedPlan.title}
                </h2>
              </div>
              <button type="button" className={styles.closeButton} onClick={closePreview}>
                Close
              </button>
            </div>

            <p className={styles.modalDescription}>
              {selectedPlan.description || "No description added."}
            </p>

            <dl className={styles.modalMeta}>
              <div>
                <dt>Uploaded by</dt>
                <dd>{selectedPlan.uploaderName}</dd>
              </div>
              <div>
                <dt>File</dt>
                <dd>
                  {selectedPlan.originalName} - {formatBytes(selectedPlan.size)}
                </dd>
              </div>
              <div>
                <dt>Date</dt>
                <dd>{formatDate(selectedPlan.uploadedAt)}</dd>
              </div>
            </dl>

            {isStudioPlan && (
              <div className={styles.previewToggleRow}>
                <button
                  type="button"
                  className={`${styles.previewToggleBtn} ${!show3D ? styles.previewToggleActive : ""}`}
                  onClick={() => setShow3D(false)}
                >
                  2D Floor Plan
                </button>
                <button
                  type="button"
                  className={`${styles.previewToggleBtn} ${show3D ? styles.previewToggleActive : ""}`}
                  onClick={() => setShow3D(true)}
                >
                  View in 3D
                </button>
              </div>
            )}

            <div className={styles.previewShell}>{renderPreviewContent(selectedPlan)}</div>

            {renderCommentPanel(selectedPlan, "modal", isLibraryMode)}

            <div className={styles.modalActions}>
              <a
                className={styles.downloadButton}
                href={`/api/floor-plans/${selectedPlan.id}/download`}
                download
              >
                Download Image
              </a>
              {isStudioPlan && (
                <button
                  type="button"
                  className={styles.downloadButton}
                  onClick={() => void downloadStudioIfc()}
                  disabled={isDownloadingIfc}
                >
                  {isDownloadingIfc ? "Generating IFC..." : "Download IFC"}
                </button>
              )}
            </div>
          </section>
        </div>
      ) : null}

    </div>
  );
}
