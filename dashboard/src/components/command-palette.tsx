"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { Dialog as DialogPrimitive } from "radix-ui";
import { Command } from "cmdk";
import {
  LayoutDashboard,
  FlaskConical,
  BookOpen,
  Rocket,
  TestTubes,
  Settings,
  Zap,
  Search,
  Clock,
  Heart,
  RefreshCw,
  Activity,
  Briefcase,
  Users,
  FileText,
  Folder,
} from "lucide-react";
import { SKILL_SAMPLES } from "@/lib/constants";
import { fetchHealth, fetchJobs, fetchClients, fetchKnowledgeBase, fetchSkills } from "@/lib/api";
import type { JobListItem, ClientSummary } from "@/lib/types";
import { toast } from "sonner";

const PAGES = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Run", href: "/run", icon: FlaskConical },
  { name: "Batch Processing", href: "/run?tab=batch", icon: FlaskConical },
  { name: "Outbound Home", href: "/outbound", icon: Rocket },
  { name: "Campaigns", href: "/outbound/campaigns", icon: Rocket },
  { name: "Sequences", href: "/outbound/sequences", icon: Rocket },
  { name: "Review Queue", href: "/outbound/review", icon: Rocket },
  { name: "Analyze Home", href: "/analyze", icon: Activity },
  { name: "Research", href: "/analyze/research", icon: Search },
  { name: "Scoring", href: "/analyze/scoring", icon: Activity },
  { name: "Plays", href: "/analyze/plays", icon: Folder },
  { name: "Context Hub", href: "/context", icon: BookOpen },
  { name: "Skills Lab", href: "/lab", icon: TestTubes },
  { name: "Pipelines", href: "/lab", icon: TestTubes },
  { name: "Status", href: "/status", icon: Activity },
  { name: "Settings", href: "/settings", icon: Settings },
  { name: "Analytics", href: "/settings?tab=analytics", icon: Settings },
];

const SKILLS = Object.keys(SKILL_SAMPLES);

const RECENTS_KEY = "kiln_recent_palette";
const MAX_RECENTS = 5;

function getRecents(): { name: string; href: string }[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(RECENTS_KEY) || "[]");
  } catch {
    return [];
  }
}

function addRecent(name: string, href: string) {
  const recents = getRecents().filter((r) => r.href !== href);
  recents.unshift({ name, href });
  localStorage.setItem(RECENTS_KEY, JSON.stringify(recents.slice(0, MAX_RECENTS)));
}

const GROUP_HEADING_CLASSES =
  "[&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:text-clay-500 [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5";

const ITEM_CLASSES =
  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-clay-300 cursor-pointer data-[selected=true]:bg-kiln-teal/10 data-[selected=true]:text-kiln-teal";

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [recents, setRecents] = useState<{ name: string; href: string }[]>([]);
  const [searchJobs, setSearchJobs] = useState<JobListItem[]>([]);
  const [searchClients, setSearchClients] = useState<ClientSummary[]>([]);
  const [searchFiles, setSearchFiles] = useState<{ name: string; path: string; driveId: string }[]>([]);
  const router = useRouter();
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  useEffect(() => {
    if (open) {
      setRecents(getRecents());
      setQuery("");
      setSearchJobs([]);
      setSearchClients([]);
      setSearchFiles([]);
    }
  }, [open]);

  // Debounced global search
  useEffect(() => {
    if (query.length < 3) {
      setSearchJobs([]);
      setSearchClients([]);
      setSearchFiles([]);
      return;
    }
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      const q = query.toLowerCase();
      fetchJobs()
        .then((res) => {
          const matches = res.jobs.filter(
            (j) =>
              j.skill.toLowerCase().includes(q) ||
              j.id.toLowerCase().includes(q) ||
              j.status.toLowerCase().includes(q)
          );
          setSearchJobs(matches.slice(0, 5));
        })
        .catch(() => {});
      fetchClients()
        .then((res) => {
          const matches = res.clients.filter(
            (c) =>
              c.name.toLowerCase().includes(q) ||
              c.slug.toLowerCase().includes(q) ||
              c.industry?.toLowerCase().includes(q)
          );
          setSearchClients(matches.slice(0, 5));
        })
        .catch(() => {});
      // Search files (KB + skills)
      Promise.all([fetchKnowledgeBase(), fetchSkills()])
        .then(([kbRes, skillRes]) => {
          const files: { name: string; path: string; driveId: string }[] = [];
          for (const [cat, kbFiles] of Object.entries(kbRes.knowledge_base)) {
            for (const f of kbFiles) {
              if (f.name.toLowerCase().includes(q) || cat.toLowerCase().includes(q)) {
                files.push({ name: f.name, path: `Knowledge Base > ${cat} > ${f.name}`, driveId: "knowledge-base" });
              }
            }
          }
          for (const skill of skillRes.skills) {
            if (skill.toLowerCase().includes(q)) {
              files.push({ name: skill, path: `Skills > ${skill}`, driveId: "skills" });
            }
          }
          setSearchFiles(files.slice(0, 5));
        })
        .catch(() => {});
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query]);

  const navigate = useCallback(
    (href: string, name?: string) => {
      if (name) addRecent(name, href);
      router.push(href);
      setOpen(false);
    },
    [router]
  );

  const handleAction = useCallback((action: string) => {
    setOpen(false);
    switch (action) {
      case "health-check":
        fetchHealth()
          .then(() => toast.success("Backend is healthy"))
          .catch(() => toast.error("Backend is unreachable"));
        break;
      case "refresh":
        window.location.reload();
        break;
    }
  }, []);

  return (
    <DialogPrimitive.Root open={open} onOpenChange={setOpen}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=closed]:animate-out data-[state=closed]:fade-out-0" />
        <DialogPrimitive.Content className="fixed left-1/2 top-[20%] z-50 w-full max-w-lg -translate-x-1/2 data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95">
          <Command className="rounded-xl border border-clay-700 bg-clay-900 shadow-2xl overflow-hidden">
            <div className="flex items-center border-b border-clay-800 px-3">
              <Search className="h-4 w-4 text-clay-500 mr-2 shrink-0" />
              <Command.Input
                placeholder="Search pages, skills, jobs, clients..."
                value={query}
                onValueChange={setQuery}
                className="h-12 w-full bg-transparent text-clay-100 placeholder:text-clay-600 text-sm outline-none"
              />
            </div>
            <Command.List className="max-h-80 overflow-y-auto p-2">
              <Command.Empty className="py-6 text-center text-sm text-clay-500">
                No results found.
              </Command.Empty>

              {recents.length > 0 && (
                <Command.Group heading="Recent" className={GROUP_HEADING_CLASSES}>
                  {recents.map((item) => (
                    <Command.Item
                      key={`recent-${item.href}`}
                      value={`recent ${item.name}`}
                      onSelect={() => navigate(item.href, item.name)}
                      className={ITEM_CLASSES}
                    >
                      <Clock className="h-4 w-4" />
                      {item.name}
                    </Command.Item>
                  ))}
                </Command.Group>
              )}

              {/* Global search: Jobs */}
              {searchJobs.length > 0 && (
                <Command.Group heading="Jobs" className={GROUP_HEADING_CLASSES}>
                  {searchJobs.map((job) => (
                    <Command.Item
                      key={`job-${job.id}`}
                      value={`job ${job.id} ${job.skill} ${job.status}`}
                      onSelect={() => navigate(`/?job=${job.id}`, `Job ${job.id.slice(0, 8)}`)}
                      className={ITEM_CLASSES}
                    >
                      <Briefcase className="h-4 w-4" />
                      <span className="flex-1 truncate">
                        <span className="text-kiln-teal">{job.skill}</span>
                        <span className="text-clay-600 mx-1.5">{job.id.slice(0, 8)}</span>
                        <span className={`text-xs ${job.status === "failed" ? "text-kiln-coral" : "text-clay-500"}`}>
                          {job.status}
                        </span>
                      </span>
                    </Command.Item>
                  ))}
                </Command.Group>
              )}

              {/* Global search: Clients */}
              {searchClients.length > 0 && (
                <Command.Group heading="Clients" className={GROUP_HEADING_CLASSES}>
                  {searchClients.map((client) => (
                    <Command.Item
                      key={`client-${client.slug}`}
                      value={`client ${client.name} ${client.slug}`}
                      onSelect={() => navigate(`/context`, client.name)}
                      className={ITEM_CLASSES}
                    >
                      <Users className="h-4 w-4" />
                      <span className="flex-1 truncate">
                        {client.name}
                        {client.industry && (
                          <span className="text-clay-600 ml-1.5 text-xs">{client.industry}</span>
                        )}
                      </span>
                    </Command.Item>
                  ))}
                </Command.Group>
              )}

              {/* Global search: Files */}
              {searchFiles.length > 0 && (
                <Command.Group heading="Files" className={GROUP_HEADING_CLASSES}>
                  {searchFiles.map((file, i) => (
                    <Command.Item
                      key={`file-${i}-${file.name}`}
                      value={`file ${file.name} ${file.path}`}
                      onSelect={() => navigate(`/context`, file.name)}
                      className={ITEM_CLASSES}
                    >
                      {file.driveId === "skills" ? (
                        <TestTubes className="h-4 w-4" />
                      ) : (
                        <FileText className="h-4 w-4" />
                      )}
                      <span className="flex-1 truncate">
                        <span className="text-clay-200">{file.name}</span>
                        <span className="text-clay-600 ml-1.5 text-xs">{file.path}</span>
                      </span>
                    </Command.Item>
                  ))}
                </Command.Group>
              )}

              <Command.Group heading="Pages" className={GROUP_HEADING_CLASSES}>
                {PAGES.map((page) => (
                  <Command.Item
                    key={page.href}
                    value={page.name}
                    onSelect={() => navigate(page.href, page.name)}
                    className={ITEM_CLASSES}
                  >
                    <page.icon className="h-4 w-4" />
                    {page.name}
                  </Command.Item>
                ))}
              </Command.Group>

              <Command.Group heading="Actions" className={GROUP_HEADING_CLASSES}>
                <Command.Item
                  value="Health Check"
                  onSelect={() => handleAction("health-check")}
                  className={ITEM_CLASSES}
                >
                  <Heart className="h-4 w-4" />
                  Health Check
                </Command.Item>
                <Command.Item
                  value="Refresh Dashboard"
                  onSelect={() => handleAction("refresh")}
                  className={ITEM_CLASSES}
                >
                  <RefreshCw className="h-4 w-4" />
                  Refresh Dashboard
                </Command.Item>
              </Command.Group>

              <Command.Group heading="Skills" className={GROUP_HEADING_CLASSES}>
                {SKILLS.map((skill) => (
                  <Command.Item
                    key={skill}
                    value={`skill ${skill}`}
                    onSelect={() => navigate(`/run?skill=${skill}`, `Run ${skill}`)}
                    className={ITEM_CLASSES}
                  >
                    <Zap className="h-4 w-4" />
                    Run {skill}
                  </Command.Item>
                ))}
              </Command.Group>
            </Command.List>

            <div className="border-t border-clay-800 px-3 py-2 flex items-center gap-4 text-xs text-clay-600">
              <span>Navigate <kbd className="ml-1 rounded border border-clay-700 bg-clay-800 px-1.5 py-0.5 font-mono text-clay-400">Enter</kbd></span>
              <span>Close <kbd className="ml-1 rounded border border-clay-700 bg-clay-800 px-1.5 py-0.5 font-mono text-clay-400">Esc</kbd></span>
              <span>Shortcuts <kbd className="ml-1 rounded border border-clay-700 bg-clay-800 px-1.5 py-0.5 font-mono text-clay-400">?</kbd></span>
            </div>
          </Command>
          <DialogPrimitive.Title className="sr-only">Command Palette</DialogPrimitive.Title>
          <DialogPrimitive.Description className="sr-only">Search for pages, skills, and actions</DialogPrimitive.Description>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
