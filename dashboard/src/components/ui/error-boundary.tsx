"use client";

import { Component, type ReactNode } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AlertTriangle, RotateCcw } from "lucide-react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("ErrorBoundary caught:", error, info);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <Card className="border-kiln-coral/30 bg-kiln-coral/5">
          <CardContent className="flex flex-col items-center justify-center py-8 text-center">
            <AlertTriangle className="h-10 w-10 text-kiln-coral mb-3" />
            <p className="text-clay-200 font-medium mb-1">Something went wrong</p>
            <p className="text-sm text-clay-300 mb-4 max-w-sm">
              {this.state.error?.message || "An unexpected error occurred."}
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => this.setState({ hasError: false, error: null })}
              className="border-kiln-coral/30 text-kiln-coral hover:bg-kiln-coral/10"
            >
              <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
              Reload section
            </Button>
          </CardContent>
        </Card>
      );
    }
    return this.props.children;
  }
}
