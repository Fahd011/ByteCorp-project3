import React, { useState } from "react";

interface ScheduleConfigProps {
  isScheduled: boolean;
  scheduleType: "weekly" | "daily" | "monthly" | "custom";
  scheduleConfig: {
    day_of_week: number;
    hour: number;
    minute: number;
    cron_expression: string;
  };
  onScheduleChange: (config: any) => void;
}

const ScheduleConfig: React.FC<ScheduleConfigProps> = ({
  isScheduled,
  scheduleType,
  scheduleConfig,
  onScheduleChange,
}) => {
  const [localConfig, setLocalConfig] = useState(scheduleConfig);

  const handleScheduleToggle = (checked: boolean) => {
    console.log("🔄 Schedule toggle changed:", checked);
    const newConfig = {
      is_scheduled: checked,
      schedule_type: checked ? scheduleType : undefined,
      schedule_config: checked ? localConfig : undefined,
    };
    console.log("📤 Sending schedule config:", newConfig);
    onScheduleChange(newConfig);
  };

  const handleScheduleTypeChange = (
    type: "weekly" | "daily" | "monthly" | "custom"
  ) => {
    console.log("🔄 Schedule type changed:", type);
    const newConfig = {
      is_scheduled: isScheduled,
      schedule_type: type,
      schedule_config: localConfig,
    };
    console.log("📤 Sending schedule config:", newConfig);
    onScheduleChange(newConfig);
  };

  const handleConfigChange = (field: string, value: any) => {
    console.log("🔄 Config field changed:", field, "=", value);
    const newConfig = { ...localConfig, [field]: value };
    setLocalConfig(newConfig);
    const fullConfig = {
      is_scheduled: isScheduled,
      schedule_type: scheduleType,
      schedule_config: newConfig,
    };
    console.log("📤 Sending full config:", fullConfig);
    onScheduleChange(fullConfig);
  };

  const getDayName = (day: number) => {
    const days = [
      "Sunday",
      "Monday",
      "Tuesday",
      "Wednesday",
      "Thursday",
      "Friday",
      "Saturday",
    ];
    return days[day];
  };

  if (!isScheduled) {
    return (
      <div style={styles.container}>
        <label style={styles.label}>
          <input
            type="checkbox"
            checked={isScheduled}
            onChange={(e) => handleScheduleToggle(e.target.checked)}
          />
          Schedule this job to run automatically
        </label>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <label style={styles.label}>
        <input
          type="checkbox"
          checked={isScheduled}
          onChange={(e) => handleScheduleToggle(e.target.checked)}
        />
        Schedule this job to run automatically
      </label>

      {isScheduled && (
        <div style={styles.scheduleOptions}>
          <div style={styles.field}>
            <label>Schedule Type:</label>
            <select
              value={scheduleType}
              onChange={(e) =>
                handleScheduleTypeChange(
                  e.target.value as "weekly" | "daily" | "monthly" | "custom"
                )
              }
              style={styles.select}
            >
              <option value="weekly">Weekly</option>
              <option value="daily">Daily</option>
              <option value="monthly">Monthly</option>
              <option value="custom">Custom Cron</option>
            </select>
          </div>

          {scheduleType === "weekly" && (
            <div style={styles.field}>
              <label>Day of Week:</label>
              <select
                value={localConfig.day_of_week}
                onChange={(e) =>
                  handleConfigChange("day_of_week", parseInt(e.target.value))
                }
                style={styles.select}
              >
                {[0, 1, 2, 3, 4, 5, 6].map((day) => (
                  <option key={day} value={day}>
                    {getDayName(day)}
                  </option>
                ))}
              </select>
            </div>
          )}

          {(scheduleType === "weekly" || scheduleType === "daily") && (
            <>
              <div style={styles.field}>
                <label>Hour (24h):</label>
                <select
                  value={localConfig.hour}
                  onChange={(e) =>
                    handleConfigChange("hour", parseInt(e.target.value))
                  }
                  style={styles.select}
                >
                  {Array.from({ length: 24 }, (_, i) => (
                    <option key={i} value={i}>
                      {i.toString().padStart(2, "0")}
                    </option>
                  ))}
                </select>
              </div>

              <div style={styles.field}>
                <label>Minute:</label>
                <select
                  value={localConfig.minute}
                  onChange={(e) =>
                    handleConfigChange("minute", parseInt(e.target.value))
                  }
                  style={styles.select}
                >
                  {Array.from({ length: 60 }, (_, i) => (
                    <option key={i} value={i}>
                      {i.toString().padStart(2, "0")}
                    </option>
                  ))}
                </select>
              </div>
            </>
          )}

          {scheduleType === "custom" && (
            <div style={styles.field}>
              <label>Cron Expression:</label>
              <input
                type="text"
                value={localConfig.cron_expression}
                onChange={(e) =>
                  handleConfigChange("cron_expression", e.target.value)
                }
                placeholder="0 9 * * 1 (Monday 9:00 AM)"
                style={styles.input}
              />
              <small style={styles.helpText}>
                Format: minute hour day month day-of-week
              </small>
            </div>
          )}

          <div style={styles.nextRun}>
            <strong>Next Run:</strong> {getNextRunDisplay()}
          </div>
        </div>
      )}
    </div>
  );

  function getNextRunDisplay() {
    if (scheduleType === "weekly") {
      const dayName = getDayName(localConfig.day_of_week);
      const time = `${localConfig.hour
        .toString()
        .padStart(2, "0")}:${localConfig.minute.toString().padStart(2, "0")}`;
      return `Every ${dayName} at ${time}`;
    } else if (scheduleType === "daily") {
      const time = `${localConfig.hour
        .toString()
        .padStart(2, "0")}:${localConfig.minute.toString().padStart(2, "0")}`;
      return `Every day at ${time}`;
    } else if (scheduleType === "custom") {
      return `Custom: ${localConfig.cron_expression}`;
    }
    return "Not scheduled";
  }
};

const styles = {
  container: {
    marginTop: "20px",
    padding: "15px",
    border: "1px solid #ddd",
    borderRadius: "8px",
    backgroundColor: "#f9f9f9",
  },
  label: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    fontWeight: "bold",
    marginBottom: "15px",
  },
  scheduleOptions: {
    marginTop: "15px",
  },
  field: {
    marginBottom: "15px",
    display: "flex",
    flexDirection: "column" as const,
    gap: "5px",
  },
  select: {
    padding: "8px",
    borderRadius: "4px",
    border: "1px solid #ccc",
    fontSize: "14px",
  },
  input: {
    padding: "8px",
    borderRadius: "4px",
    border: "1px solid #ccc",
    fontSize: "14px",
  },
  helpText: {
    fontSize: "12px",
    color: "#666",
    fontStyle: "italic",
  },
  nextRun: {
    marginTop: "15px",
    padding: "10px",
    backgroundColor: "#e3f2fd",
    borderRadius: "4px",
    border: "1px solid #2196f3",
  },
};

export default ScheduleConfig;
