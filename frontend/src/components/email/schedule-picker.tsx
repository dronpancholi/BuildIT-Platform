"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Calendar, Clock } from "lucide-react";

interface SchedulePickerProps {
  scheduledAt: string | null;
  onChange: (isoDate: string | null) => void;
}

export function SchedulePicker({ scheduledAt, onChange }: SchedulePickerProps) {
  const [showPicker, setShowPicker] = useState(false);

  const handleSchedule = () => {
    const now = new Date();
    now.setHours(now.getHours() + 1, 0, 0, 0);
    onChange(now.toISOString());
    setShowPicker(false);
  };

  const handleCancel = () => {
    onChange(null);
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() => setShowPicker(!showPicker)}
          className="h-8 border-platform-500/50 text-platform-400 hover:bg-platform-500/10 text-xs gap-1"
        >
          <Calendar className="w-3.5 h-3.5" />
          {scheduledAt ? "Reschedule" : "Schedule Send"}
        </Button>
        {scheduledAt && (
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={handleCancel}
            className="h-8 text-xs text-slate-500 hover:text-red-400"
          >
            Clear Schedule
          </Button>
        )}
      </div>

      {scheduledAt && (
        <div className="flex items-center gap-2 text-xs text-slate-400 bg-surface-darker px-3 py-1.5 rounded border border-surface-border">
          <Clock className="w-3 h-3" />
          Scheduled for: {new Date(scheduledAt).toLocaleString()}
        </div>
      )}

      {showPicker && !scheduledAt && (
        <div className="p-3 bg-surface-card border border-surface-border rounded-lg space-y-2">
          <p className="text-xs text-slate-400">
            Schedule this email for later delivery:
          </p>
          <div className="flex items-center gap-2">
            <input
              type="datetime-local"
              className="flex-1 px-3 py-1.5 text-xs bg-surface-darker border border-surface-border rounded text-slate-200 focus:outline-none focus:border-platform-500"
              min={new Date().toISOString().slice(0, 16)}
              onChange={(e) => {
                if (e.target.value) {
                  onChange(new Date(e.target.value).toISOString());
                }
              }}
            />
          </div>
          <div className="flex gap-2">
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={handleSchedule}
              className="text-xs h-7"
            >
              +1 Hour
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => {
                const d = new Date();
                d.setDate(d.getDate() + 1);
                d.setHours(9, 0, 0, 0);
                onChange(d.toISOString());
              }}
              className="text-xs h-7"
            >
              Tomorrow 9AM
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => {
                const d = new Date();
                d.setDate(d.getDate() + 7);
                d.setHours(9, 0, 0, 0);
                onChange(d.toISOString());
              }}
              className="text-xs h-7"
            >
              Next Week
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
