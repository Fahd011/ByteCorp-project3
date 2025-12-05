interface Tab {
  key: string;
  label: string;
}

interface StatusTabsProps<T extends string> {
  tabs: readonly Tab[];
  activeTab: T;
  onTabChange: (tab: T) => void;
  className?: string;
}

export function StatusTabs<T extends string>({ 
  tabs, 
  activeTab, 
  onTabChange,
  className = "mb-6"
}: StatusTabsProps<T>) {
  return (
    <div className={`flex gap-2 border-b border-border ${className}`}>
      {tabs.map((tab) => (
        <button
          key={tab.key}
          onClick={() => onTabChange(tab.key as T)}
          className={`px-4 py-3 text-sm font-medium transition-colors relative ${
            activeTab === tab.key
              ? "text-foreground"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          {tab.label}
          {activeTab === tab.key && (
            <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />
          )}
        </button>
      ))}
    </div>
  );
}

