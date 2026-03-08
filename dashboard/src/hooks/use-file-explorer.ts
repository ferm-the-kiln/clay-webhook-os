"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import type {
  FileNode,
  FileNodeType,
  DriveId,
  KnowledgeBaseFile,
  ClientSummary,
  SkillFile,
} from "@/lib/types";
import {
  fetchKnowledgeBase,
  fetchClients,
  fetchSkills,
  fetchSkillContent,
  fetchContextUsageMap,
} from "@/lib/api";
import { toast } from "sonner";

// ── Storage keys ──────────────────────────────────────────────
const STORAGE_KEYS = {
  viewMode: "kiln_explorer_view",
  favorites: "kiln_explorer_favorites",
  expanded: "kiln_explorer_expanded",
} as const;

function readStorage<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    const v = localStorage.getItem(key);
    return v ? JSON.parse(v) : fallback;
  } catch {
    return fallback;
  }
}

// ── Tree builder ──────────────────────────────────────────────

function buildFileTree(
  kbFiles: Record<string, KnowledgeBaseFile[]>,
  clients: ClientSummary[],
  skillNames: string[]
): FileNode[] {
  const drives: FileNode[] = [];

  // Knowledge Base drive
  const kbChildren: FileNode[] = Object.keys(kbFiles)
    .sort()
    .map((category) => {
      const files = kbFiles[category].map(
        (f): FileNode => ({
          id: `kb:${f.path}`,
          name: f.name.endsWith(".md") ? f.name : `${f.name}.md`,
          type: "file" as FileNodeType,
          driveId: "knowledge-base",
          parentId: `kb:${category}`,
          category: f.category,
          content: f.content,
          meta: { path: f.path },
        })
      );
      return {
        id: `kb:${category}`,
        name: category,
        type: "folder" as FileNodeType,
        driveId: "knowledge-base" as DriveId,
        parentId: "drive:knowledge-base",
        children: files,
      };
    });
  drives.push({
    id: "drive:knowledge-base",
    name: "Knowledge Base",
    type: "drive",
    driveId: "knowledge-base",
    parentId: null,
    children: kbChildren,
  });

  // Clients drive
  const clientFiles: FileNode[] = clients.map(
    (c): FileNode => ({
      id: `client:${c.slug}`,
      name: c.name || c.slug,
      type: "file",
      driveId: "clients",
      parentId: "drive:clients",
      slug: c.slug,
      meta: { industry: c.industry, stage: c.stage, domain: c.domain },
    })
  );
  drives.push({
    id: "drive:clients",
    name: "Clients",
    type: "drive",
    driveId: "clients",
    parentId: null,
    children: clientFiles,
  });

  // Skills drive
  const skillFiles: FileNode[] = skillNames.map(
    (name): FileNode => ({
      id: `skill:${name}`,
      name: `${name}`,
      type: "file",
      driveId: "skills",
      parentId: "drive:skills",
      slug: name,
    })
  );
  drives.push({
    id: "drive:skills",
    name: "Skills",
    type: "drive",
    driveId: "skills",
    parentId: null,
    children: skillFiles,
  });

  return drives;
}

// ── Hook ──────────────────────────────────────────────────────

export type ViewMode = "grid" | "list";

export interface FileTab {
  id: string;
  label: string;
  nodeId: string;
}

export function useFileExplorer() {
  // Raw data
  const [kbFiles, setKbFiles] = useState<Record<string, KnowledgeBaseFile[]>>({});
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [skillNames, setSkillNames] = useState<string[]>([]);
  const [usageMap, setUsageMap] = useState<Record<string, string[]>>({});
  const [loading, setLoading] = useState(true);

  // Explorer state
  const [currentPath, setCurrentPath] = useState<string[]>(["root"]);
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>(() =>
    readStorage(STORAGE_KEYS.viewMode, "grid" as ViewMode)
  );
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(
    () => new Set(readStorage<string[]>(STORAGE_KEYS.expanded, []))
  );
  const [searchQuery, setSearchQuery] = useState("");
  const [previewOpen, setPreviewOpen] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [splitFileId, setSplitFileId] = useState<string | null>(null);

  // Tabs
  const [openTabs, setOpenTabs] = useState<FileTab[]>([
    { id: "tab:root", label: "Root", nodeId: "root" },
  ]);
  const [activeTabId, setActiveTabId] = useState("tab:root");

  // Favorites
  const [favorites, setFavorites] = useState<string[]>(() =>
    readStorage(STORAGE_KEYS.favorites, [])
  );

  // Multi-select
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // File tree
  const fileTree = useMemo(
    () => buildFileTree(kbFiles, clients, skillNames),
    [kbFiles, clients, skillNames]
  );

  // Flat lookup
  const nodeMap = useMemo(() => {
    const map = new Map<string, FileNode>();
    function walk(nodes: FileNode[]) {
      for (const n of nodes) {
        map.set(n.id, n);
        if (n.children) walk(n.children);
      }
    }
    walk(fileTree);
    return map;
  }, [fileTree]);

  // ── Persist ────────────────────────────────────────────────
  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.viewMode, JSON.stringify(viewMode));
  }, [viewMode]);

  useEffect(() => {
    localStorage.setItem(
      STORAGE_KEYS.favorites,
      JSON.stringify(favorites)
    );
  }, [favorites]);

  useEffect(() => {
    localStorage.setItem(
      STORAGE_KEYS.expanded,
      JSON.stringify([...expandedFolders])
    );
  }, [expandedFolders]);

  // ── Data loading ───────────────────────────────────────────
  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [kbRes, clientRes, skillRes] = await Promise.all([
        fetchKnowledgeBase(),
        fetchClients(),
        fetchSkills(),
      ]);
      setKbFiles(kbRes.knowledge_base);
      setClients(clientRes.clients);
      setSkillNames(skillRes.skills);
    } catch {
      toast.error("Failed to load file explorer data");
    } finally {
      setLoading(false);
    }
    // Load usage map in background (non-critical)
    fetchContextUsageMap()
      .then((res) => setUsageMap(res.usage_map))
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  // ── Current folder contents ────────────────────────────────
  const currentFolderId = currentPath[currentPath.length - 1];

  const currentFolderContents = useMemo(() => {
    if (currentFolderId === "root") return fileTree;
    const node = nodeMap.get(currentFolderId);
    return node?.children ?? [];
  }, [currentFolderId, fileTree, nodeMap]);

  const filteredContents = useMemo(() => {
    if (!searchQuery.trim()) return currentFolderContents;
    const q = searchQuery.toLowerCase();
    return currentFolderContents.filter((n) =>
      n.name.toLowerCase().includes(q)
    );
  }, [currentFolderContents, searchQuery]);

  // ── Breadcrumbs ────────────────────────────────────────────
  const breadcrumbs = useMemo(() => {
    return currentPath.map((id) => {
      if (id === "root") return { id, name: "Root" };
      const node = nodeMap.get(id);
      return { id, name: node?.name ?? id };
    });
  }, [currentPath, nodeMap]);

  // ── Favorite nodes ─────────────────────────────────────────
  const favoriteNodes = useMemo(() => {
    return favorites
      .map((id) => nodeMap.get(id))
      .filter((n): n is FileNode => n !== undefined);
  }, [favorites, nodeMap]);

  // ── Selected file node ─────────────────────────────────────
  const selectedFile = useMemo(
    () => (selectedFileId ? nodeMap.get(selectedFileId) ?? null : null),
    [selectedFileId, nodeMap]
  );

  // ── Actions ────────────────────────────────────────────────
  const navigateTo = useCallback(
    (nodeId: string) => {
      if (nodeId === "root") {
        setCurrentPath(["root"]);
        setSearchQuery("");
        return;
      }
      // Build path from root to this node
      const path: string[] = ["root"];
      const node = nodeMap.get(nodeId);
      if (!node) return;

      // For drives: path = [root, driveId]
      if (node.type === "drive") {
        path.push(node.id);
      } else if (node.type === "folder") {
        // path = [root, driveId, folderId]
        const driveId = `drive:${node.driveId}`;
        path.push(driveId, node.id);
      } else {
        // File — navigate to parent
        if (node.parentId) {
          const parent = nodeMap.get(node.parentId);
          if (parent?.type === "drive") {
            path.push(parent.id);
          } else if (parent) {
            const driveId = `drive:${parent.driveId}`;
            path.push(driveId, parent.id);
          }
        }
      }
      setCurrentPath(path);
      setSearchQuery("");
    },
    [nodeMap]
  );

  const selectFile = useCallback(
    (nodeId: string | null) => {
      setSelectedFileId(nodeId);
      if (nodeId) {
        setPreviewOpen(true);
        setEditMode(false);
      }
    },
    []
  );

  const toggleFolder = useCallback((folderId: string) => {
    setExpandedFolders((prev) => {
      const next = new Set(prev);
      if (next.has(folderId)) next.delete(folderId);
      else next.add(folderId);
      return next;
    });
  }, []);

  const openTab = useCallback(
    (nodeId: string) => {
      const node = nodeMap.get(nodeId);
      const label = node?.name ?? nodeId;
      const existing = openTabs.find((t) => t.nodeId === nodeId);
      if (existing) {
        setActiveTabId(existing.id);
      } else {
        const tab: FileTab = {
          id: `tab:${nodeId}:${Date.now()}`,
          label,
          nodeId,
        };
        setOpenTabs((prev) => [...prev, tab]);
        setActiveTabId(tab.id);
      }
      navigateTo(nodeId);
    },
    [nodeMap, openTabs, navigateTo]
  );

  const closeTab = useCallback(
    (tabId: string) => {
      setOpenTabs((prev) => {
        const next = prev.filter((t) => t.id !== tabId);
        if (next.length === 0) {
          const root: FileTab = { id: "tab:root", label: "Root", nodeId: "root" };
          setActiveTabId(root.id);
          setCurrentPath(["root"]);
          return [root];
        }
        if (activeTabId === tabId) {
          const idx = prev.findIndex((t) => t.id === tabId);
          const newActive = next[Math.min(idx, next.length - 1)];
          setActiveTabId(newActive.id);
          navigateTo(newActive.nodeId);
        }
        return next;
      });
    },
    [activeTabId, navigateTo]
  );

  const toggleFavorite = useCallback((nodeId: string) => {
    setFavorites((prev) =>
      prev.includes(nodeId) ? prev.filter((id) => id !== nodeId) : [...prev, nodeId]
    );
  }, []);

  const startRename = useCallback((nodeId: string) => {
    setRenamingId(nodeId);
  }, []);

  const confirmRename = useCallback(() => {
    setRenamingId(null);
  }, []);

  const navigateUp = useCallback(() => {
    if (currentPath.length <= 1) return;
    setCurrentPath((prev) => prev.slice(0, -1));
  }, [currentPath]);

  const toggleSelect = useCallback(
    (nodeId: string, multi: boolean) => {
      setSelectedIds((prev) => {
        const next = new Set(multi ? prev : []);
        if (next.has(nodeId)) next.delete(nodeId);
        else next.add(nodeId);
        return next;
      });
    },
    []
  );

  const clearSelection = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  // ── All files flat (for command palette search) ────────────
  const allFiles = useMemo(() => {
    const files: FileNode[] = [];
    function walk(nodes: FileNode[]) {
      for (const n of nodes) {
        if (n.type === "file") files.push(n);
        if (n.children) walk(n.children);
      }
    }
    walk(fileTree);
    return files;
  }, [fileTree]);

  return {
    // Data
    fileTree,
    nodeMap,
    kbFiles,
    clients,
    skillNames,
    usageMap,
    loading,
    allFiles,

    // State
    currentPath,
    currentFolderId,
    currentFolderContents: filteredContents,
    selectedFileId,
    selectedFile,
    viewMode,
    expandedFolders,
    searchQuery,
    previewOpen,
    editMode,
    openTabs,
    activeTabId,
    favorites,
    favoriteNodes,
    renamingId,
    splitFileId,
    breadcrumbs,
    selectedIds,

    // Setters
    setViewMode,
    setSearchQuery,
    setPreviewOpen,
    setEditMode,
    setSplitFileId,

    // Actions
    navigateTo,
    navigateUp,
    selectFile,
    toggleFolder,
    openTab,
    closeTab,
    toggleFavorite,
    startRename,
    confirmRename,
    toggleSelect,
    clearSelection,
    loadAll,
  };
}
