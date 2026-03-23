"use client";

import { useState, useCallback } from "react";
import { Upload, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { uploadPortalMedia } from "@/lib/api";
import { toast } from "sonner";

interface MediaUploadProps {
  slug: string;
  projectId?: string;
  onUploaded: () => void;
}

export function MediaUpload({ slug, projectId, onUploaded }: MediaUploadProps) {
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [caption, setCaption] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleFile = useCallback((file: File) => {
    setSelectedFile(file);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleUpload = async () => {
    if (!selectedFile) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("caption", caption);
      if (projectId) {
        formData.append("project_id", projectId);
      }
      await uploadPortalMedia(slug, formData);
      toast.success("File uploaded");
      setSelectedFile(null);
      setCaption("");
      onUploaded();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-3">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
          dragOver
            ? "border-kiln-teal bg-kiln-teal/5"
            : "border-clay-600 hover:border-clay-500"
        }`}
      >
        {selectedFile ? (
          <div className="flex items-center justify-center gap-3">
            <span className="text-sm text-clay-200">{selectedFile.name}</span>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setSelectedFile(null)}
              className="h-6 w-6 text-clay-400 hover:text-clay-200"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        ) : (
          <>
            <Upload className="h-8 w-8 text-clay-500 mx-auto mb-2" />
            <p className="text-sm text-clay-400 mb-2">
              Drag & drop a file here, or{" "}
              <label className="text-kiln-teal cursor-pointer hover:underline">
                browse
                <input
                  type="file"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) handleFile(file);
                  }}
                />
              </label>
            </p>
            <p className="text-[10px] text-clay-500">Images, videos, PDFs, docs — up to 50MB</p>
          </>
        )}
      </div>

      {selectedFile && (
        <div className="flex gap-2">
          <input
            type="text"
            value={caption}
            onChange={(e) => setCaption(e.target.value)}
            placeholder="Add a caption (optional)"
            className="flex-1 bg-clay-900 border border-clay-600 rounded-md px-3 py-1.5 text-sm text-clay-100 placeholder:text-clay-500 focus:outline-none focus:border-kiln-teal"
          />
          <Button
            size="sm"
            onClick={handleUpload}
            disabled={uploading}
            className="bg-kiln-teal text-clay-900 hover:bg-kiln-teal/90 gap-1.5"
          >
            <Upload className="h-3.5 w-3.5" />
            {uploading ? "Uploading..." : "Upload"}
          </Button>
        </div>
      )}
    </div>
  );
}
