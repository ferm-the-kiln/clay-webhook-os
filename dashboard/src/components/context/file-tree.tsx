"use client";

import { Star, BookOpen, Users, TestTubes, ChevronRight, ChevronDown, Folder, FolderOpen, FileText } from "lucide-react";
import { cn } from "@/lib/utils";
import type { FileNode } from "@/lib/types";
import { motion, AnimatePresence } from "framer-motion";

interface FileTreeProps {
  tree: FileNode[];
  expandedFolders: Set<string>;
  selectedFileId: string | null;
  favorites: string[];
  favoriteNodes: FileNode[];
  currentFolderId: string;
  onToggleFolder: (id: string) => void;
  onNavigate: (id: string) => void;
  onSelectFile: (id: string) => void;
  onToggleFavorite: (id: string) => void;
}

const DRIVE_ICONS: Record<string, typeof BookOpen> = {
  "knowledge-base": BookOpen,
  clients: Users,
  skills: TestTubes,
};

function TreeNode({
  node,
  depth,
  expandedFolders,
  selectedFileId,
  currentFolderId,
  onToggleFolder,
  onNavigate,
  onSelectFile,
}: {
  node: FileNode;
  depth: number;
  expandedFolders: Set<string>;
  selectedFileId: string | null;
  currentFolderId: string;
  onToggleFolder: (id: string) => void;
  onNavigate: (id: string) => void;
  onSelectFile: (id: string) => void;
}) {
  const isExpanded = expandedFolders.has(node.id);
  const isActive = node.id === currentFolderId;
  const isSelected = node.id === selectedFileId;
  const hasChildren = node.children && node.children.length > 0;
  const isDrive = node.type === "drive";
  const isFolder = node.type === "folder" || isDrive;

  const DriveIcon = isDrive ? DRIVE_ICONS[node.driveId] || Folder : undefined;
  const FolderIcon = isFolder
    ? isExpanded
      ? FolderOpen
      : Folder
    : FileText;
  const Icon = DriveIcon || FolderIcon;

  const handleClick = () => {
    if (isFolder) {
      onToggleFolder(node.id);
      onNavigate(node.id);
    } else {
      onSelectFile(node.id);
    }
  };

  return (
    <div>
      <button
        onClick={handleClick}
        className={cn(
          "flex w-full items-center gap-1.5 rounded-md px-2 py-1 text-left text-sm transition-colors",
          isActive && "bg-kiln-teal/10 text-kiln-teal",
          isSelected && !isActive && "bg-clay-800 text-clay-200",
          !isActive && !isSelected && "text-clay-400 hover:bg-clay-800/50 hover:text-clay-200"
        )}
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
      >
        {isFolder && hasChildren ? (
          isExpanded ? (
            <ChevronDown className="h-3 w-3 shrink-0 text-clay-500" />
          ) : (
            <ChevronRight className="h-3 w-3 shrink-0 text-clay-500" />
          )
        ) : (
          <span className="w-3 shrink-0" />
        )}
        <Icon className={cn("h-4 w-4 shrink-0", isDrive && "text-kiln-teal")} />
        <span className="truncate text-xs">{node.name}</span>
      </button>
      <AnimatePresence initial={false}>
        {isExpanded && hasChildren && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="overflow-hidden"
          >
            {node.children!.map((child) => (
              <TreeNode
                key={child.id}
                node={child}
                depth={depth + 1}
                expandedFolders={expandedFolders}
                selectedFileId={selectedFileId}
                currentFolderId={currentFolderId}
                onToggleFolder={onToggleFolder}
                onNavigate={onNavigate}
                onSelectFile={onSelectFile}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function FileTree({
  tree,
  expandedFolders,
  selectedFileId,
  favorites,
  favoriteNodes,
  currentFolderId,
  onToggleFolder,
  onNavigate,
  onSelectFile,
  onToggleFavorite,
}: FileTreeProps) {
  return (
    <div className="flex h-full flex-col overflow-y-auto py-2">
      {/* Favorites */}
      {favoriteNodes.length > 0 && (
        <div className="mb-2 px-2">
          <div className="flex items-center gap-1.5 px-2 py-1 text-xs font-medium uppercase tracking-wider text-clay-500">
            <Star className="h-3 w-3" />
            Favorites
          </div>
          {favoriteNodes.map((node) => (
            <button
              key={node.id}
              onClick={() =>
                node.type === "file"
                  ? onSelectFile(node.id)
                  : onNavigate(node.id)
              }
              className={cn(
                "flex w-full items-center gap-1.5 rounded-md px-2 py-1 text-xs text-clay-400 hover:bg-clay-800/50 hover:text-clay-200",
                node.id === selectedFileId && "bg-clay-800 text-clay-200"
              )}
            >
              <Star className="h-3 w-3 fill-amber-500 text-amber-500" />
              <span className="truncate">{node.name}</span>
            </button>
          ))}
          <div className="mx-2 my-2 border-t border-clay-800" />
        </div>
      )}

      {/* Tree */}
      <div className="px-1">
        {tree.map((drive) => (
          <TreeNode
            key={drive.id}
            node={drive}
            depth={0}
            expandedFolders={expandedFolders}
            selectedFileId={selectedFileId}
            currentFolderId={currentFolderId}
            onToggleFolder={onToggleFolder}
            onNavigate={onNavigate}
            onSelectFile={onSelectFile}
          />
        ))}
      </div>
    </div>
  );
}
