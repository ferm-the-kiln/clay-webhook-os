"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { fetchPortal } from "@/lib/api";
import { useProject } from "@/hooks/use-project";
import { usePortalFeed } from "@/hooks/use-portal-feed";
import { ProjectHeader } from "@/components/portal/project-header";
import { ProjectSidebar } from "@/components/portal/project-sidebar";
import { SearchBar } from "@/components/portal/search-bar";
import { PostFeed } from "@/components/portal/post-feed";
import { UpdateComposer } from "@/components/portal/update-composer";

export default function ProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const slug = params.slug as string;
  const projectId = params.projectId as string;

  const [clientName, setClientName] = useState("");
  const [composerOpen, setComposerOpen] = useState(false);

  const {
    project,
    updates,
    media,
    actions,
    stats,
    loading,
    reload,
    handleUpdateProject,
    handleDeleteProject,
    handleAddPhase,
    handleTogglePhase,
    handleDeletePhase,
    handleTogglePin,
    handleDeleteUpdate,
    handleToggleAction,
  } = useProject(slug, projectId);

  const {
    searchQuery,
    setSearchQuery,
    highlightedPostId,
    highlightPost,
    filteredUpdates,
    postRefs,
  } = usePortalFeed(updates);

  // Load client name
  useEffect(() => {
    fetchPortal(slug)
      .then((p) => setClientName(p.name))
      .catch(() => {});
  }, [slug]);

  // Keyboard: N opens composer
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "n" && !e.metaKey && !e.ctrlKey && !e.altKey) {
        const tag = (e.target as HTMLElement).tagName;
        if (tag === "INPUT" || tag === "TEXTAREA" || (e.target as HTMLElement).isContentEditable) return;
        e.preventDefault();
        setComposerOpen(true);
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleDelete = async () => {
    if (!confirm("Delete this project? Posts will be unlinked but not deleted.")) return;
    const ok = await handleDeleteProject();
    if (ok) router.push(`/clients/${slug}`);
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto space-y-4 px-4">
        <div className="h-8 bg-clay-700 rounded-lg animate-pulse w-32" />
        <div className="h-12 bg-clay-700 rounded-lg animate-pulse" />
        <div className="h-64 bg-clay-700 rounded-lg animate-pulse" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="max-w-6xl mx-auto text-center py-16 px-4">
        <p className="text-clay-400">Project not found.</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 pb-12">
      <div className="space-y-5">
        <ProjectHeader
          project={project}
          slug={slug}
          clientName={clientName || slug}
          onStatusChange={(status) => handleUpdateProject({ status })}
          onDelete={handleDelete}
        />

        {/* Create post button */}
        <div className="flex justify-end">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setComposerOpen(!composerOpen)}
            className="border-clay-600 text-clay-200 hover:bg-clay-700 gap-1.5"
          >
            <Plus className="h-3.5 w-3.5" />
            Create Post
          </Button>
        </div>

        {/* Two-column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-6">
          {/* Left: Feed */}
          <div className="space-y-4 min-w-0">
            <SearchBar
              value={searchQuery}
              onChange={setSearchQuery}
              resultCount={filteredUpdates.length}
              totalCount={updates.length}
            />

            {composerOpen && (
              <UpdateComposer
                slug={slug}
                clientName={clientName || slug}
                projectId={projectId}
                onPosted={() => {
                  reload();
                  setComposerOpen(false);
                }}
              />
            )}

            <PostFeed
              slug={slug}
              updates={filteredUpdates}
              media={media}
              searchQuery={searchQuery}
              highlightedPostId={highlightedPostId}
              postRefs={postRefs}
              onTogglePin={handleTogglePin}
              onDeleteUpdate={handleDeleteUpdate}
              clientName={clientName || slug}
            />
          </div>

          {/* Right: Sidebar */}
          <ProjectSidebar
            project={project}
            stats={stats}
            onTogglePhase={handleTogglePhase}
            onAddPhase={handleAddPhase}
            onDeletePhase={handleDeletePhase}
          />
        </div>
      </div>
    </div>
  );
}
