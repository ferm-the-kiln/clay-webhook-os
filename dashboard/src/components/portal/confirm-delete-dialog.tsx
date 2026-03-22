"use client";

import { AlertTriangle, Loader2, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface ConfirmDeleteDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  title: string;
  mediaCount: number;
  loading?: boolean;
}

export function ConfirmDeleteDialog({
  open,
  onOpenChange,
  onConfirm,
  title,
  mediaCount,
  loading,
}: ConfirmDeleteDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-clay-800 border-clay-700 sm:max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-red-400" />
            <DialogTitle className="text-clay-100">Delete Post</DialogTitle>
          </div>
          <DialogDescription className="text-clay-400 pt-2">
            {mediaCount > 0 ? (
              <>
                This will permanently delete <span className="text-clay-200 font-medium">&ldquo;{title}&rdquo;</span> and{" "}
                <span className="text-clay-200 font-medium">{mediaCount} attached file{mediaCount > 1 ? "s" : ""}</span>.
                Files will also be removed from Google Drive. This action cannot be undone.
              </>
            ) : (
              <>
                This will permanently delete <span className="text-clay-200 font-medium">&ldquo;{title}&rdquo;</span>.
                This action cannot be undone.
              </>
            )}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={loading}
            className="border-clay-600 text-clay-300 hover:text-clay-100 hover:bg-clay-700"
          >
            Cancel
          </Button>
          <Button
            onClick={onConfirm}
            disabled={loading}
            className="bg-red-600 text-white hover:bg-red-700 gap-1.5"
          >
            {loading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Trash2 className="h-3.5 w-3.5" />
            )}
            {loading ? "Deleting..." : "Delete"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
