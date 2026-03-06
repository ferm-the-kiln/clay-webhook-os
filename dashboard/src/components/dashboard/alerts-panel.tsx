"use client";

import { motion } from "framer-motion";
import {
  AlertTriangle,
  TrendingUp,
  CheckCircle2,
  Megaphone,
  ShieldAlert,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { OutcomeAlert, OutcomeRecommendation } from "@/lib/types";

interface AlertsPanelProps {
  alerts: OutcomeAlert[];
  recommendations: OutcomeRecommendation[];
}

function getAlertIcon(type: string) {
  switch (type) {
    case "quality":
      return ShieldAlert;
    case "campaign":
      return Megaphone;
    default:
      return AlertTriangle;
  }
}

function getAlertBorderColor(type: string): string {
  switch (type) {
    case "quality":
      return "border-l-kiln-coral";
    case "campaign":
      return "border-l-kiln-mustard";
    default:
      return "border-l-kiln-mustard";
  }
}

function getAlertIconColor(type: string): string {
  switch (type) {
    case "quality":
      return "text-kiln-coral";
    case "campaign":
      return "text-kiln-mustard";
    default:
      return "text-kiln-mustard";
  }
}

export function AlertsPanel({ alerts, recommendations }: AlertsPanelProps) {
  const hasContent = alerts.length > 0 || recommendations.length > 0;

  return (
    <div className="space-y-4">
      <h3 className="text-xs text-clay-500 uppercase tracking-wide font-[family-name:var(--font-sans)]">
        Alerts & Recommendations
      </h3>

      {!hasContent ? (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <Card className="bg-clay-800 border-clay-700">
            <CardContent className="p-5">
              <div className="flex items-center gap-3">
                <div className="flex items-center justify-center h-8 w-8 rounded-full bg-kiln-teal/10">
                  <CheckCircle2 className="h-4 w-4 text-kiln-teal" />
                </div>
                <div>
                  <p className="text-sm text-clay-200">All systems healthy</p>
                  <p className="text-xs text-clay-500">
                    No alerts or recommendations at this time
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      ) : (
        <div className="space-y-2">
          {/* Alerts */}
          {alerts.map((alert, index) => {
            const Icon = getAlertIcon(alert.type);
            const borderColor = getAlertBorderColor(alert.type);
            const iconColor = getAlertIconColor(alert.type);

            return (
              <motion.div
                key={`alert-${index}`}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: index * 0.05 }}
              >
                <Card
                  className={cn(
                    "bg-clay-800 border-clay-700 border-l-3",
                    borderColor
                  )}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start gap-3">
                      <Icon
                        className={cn("h-4 w-4 mt-0.5 shrink-0", iconColor)}
                      />
                      <div className="min-w-0 flex-1">
                        <p className="text-sm text-clay-200">
                          {alert.message}
                        </p>
                        {alert.campaign_name && (
                          <p className="text-xs text-clay-500 mt-0.5">
                            Campaign: {alert.campaign_name}
                          </p>
                        )}
                        {alert.skill && (
                          <p className="text-xs text-clay-500 mt-0.5">
                            Skill: {alert.skill}
                          </p>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            );
          })}

          {/* Recommendations */}
          {recommendations.map((rec, index) => (
            <motion.div
              key={`rec-${index}`}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{
                duration: 0.3,
                delay: (alerts.length + index) * 0.05,
              }}
            >
              <Card className="bg-clay-800 border-clay-700">
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    <TrendingUp className="h-4 w-4 mt-0.5 shrink-0 text-clay-400" />
                    <p className="text-sm text-clay-300">{rec.message}</p>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
